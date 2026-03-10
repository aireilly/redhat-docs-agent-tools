#!/usr/bin/env ruby
# frozen_string_literal: true

# line_break.rb
# Removes hard line breaks from AsciiDoc files for DITA compatibility.
# Usage: ruby line_break.rb <file.adoc> [-o output.adoc] [--dry-run]

require 'tempfile'
require 'fileutils'

def process_file(path)
  content = File.read(path, encoding: 'UTF-8')
  lines = content.lines.map(&:chomp)

  in_comment_block = false
  comment_delimiter = nil
  in_code_block = false
  code_delimiter = nil
  removal_count = 0
  skip_indices = []

  processed_lines = []
  i = 0

  while i < lines.length
    line = lines[i]

    # Track comment blocks
    if line =~ %r{^/{4,}\s*$}
      delimiter = line.strip
      if !in_comment_block
        in_comment_block = true
        comment_delimiter = delimiter
      elsif comment_delimiter == delimiter
        in_comment_block = false
        comment_delimiter = nil
      end
      processed_lines << line
      i += 1
      next
    end

    if in_comment_block
      processed_lines << line
      i += 1
      next
    end

    # Track code blocks (---- or ....)
    if line =~ /^(\.{4,}|-{4,})\s*$/
      delimiter = line.strip
      if !in_code_block
        in_code_block = true
        code_delimiter = delimiter
      elsif code_delimiter && line.strip.start_with?(code_delimiter[0]) &&
            line.strip.length >= code_delimiter.length
        in_code_block = false
        code_delimiter = nil
      end
      processed_lines << line
      i += 1
      next
    end

    if in_code_block
      processed_lines << line
      i += 1
      next
    end

    # Remove :hardbreaks-option: attribute
    if line =~ /^:hardbreaks-option:(?:|\s.*)$/
      removal_count += 1
      i += 1
      next
    end

    # Remove %hardbreaks from block attribute lists
    if line =~ /^\[.*%hardbreaks.*\]/
      new_line = line.gsub(/%hardbreaks,?\s*/, '').gsub(/,\s*%hardbreaks/, '')
      # If the attribute list is now empty except for brackets, remove it
      if new_line =~ /^\[\s*\]$/
        removal_count += 1
        i += 1
        next
      end
      processed_lines << new_line
      removal_count += 1
      i += 1
      next
    end

    # Remove options=hardbreaks from block attribute lists
    if line =~ /^\[.*options=["']?[^"'\]]*hardbreaks[^"'\]]*["']?.*\]/
      new_line = line.gsub(/options=["']?hardbreaks["']?,?\s*/, '')
                     .gsub(/,?\s*options=["']?hardbreaks["']?/, '')
      # Clean up options containing hardbreaks among other options
      new_line = new_line.gsub(/hardbreaks,?\s*/, '').gsub(/,\s*hardbreaks/, '')
      if new_line =~ /^\[\s*\]$/
        removal_count += 1
        i += 1
        next
      end
      processed_lines << new_line
      removal_count += 1
      i += 1
      next
    end

    # Handle line continuation with ` +` at end of line
    # Pattern: not starting with // (comment), at least one char before ` +`
    if line =~ /^(?:[^\/]{2}|.{1}).*\s\+\s*$/ || line =~ /^.\s\+\s*$/
      # Remove the ` +` and join with the next non-empty line
      cleaned_line = line.sub(/\s\+\s*$/, '')

      # Look ahead for the next content line to join
      j = i + 1
      while j < lines.length
        next_line = lines[j]

        # Skip empty lines when joining
        if next_line =~ /^\s*$/
          j += 1
          next
        end

        # Don't join if next line is a structural element
        break if next_line =~ /^(=+\s|\.(?:[A-Z]|[a-z])|\[|include::|image::|:[\w-]+:)/

        # Join the lines
        cleaned_line = "#{cleaned_line} #{next_line.strip}"
        skip_indices << j
        removal_count += 1
        break
      end

      processed_lines << cleaned_line
      i += 1
      next
    end

    # Skip lines that were joined to previous lines
    if skip_indices.include?(i)
      i += 1
      next
    end

    processed_lines << line
    i += 1
  end

  { lines: processed_lines, count: removal_count }
end

# Parse command line arguments
input_file = nil
output_file = nil
dry_run = false

i = 0
while i < ARGV.length
  arg = ARGV[i]
  case arg
  when '-o'
    if i + 1 < ARGV.length
      output_file = ARGV[i + 1]
      i += 2
    else
      puts 'Error: -o requires an argument'
      exit 1
    end
  when /^-o(.+)$/
    output_file = Regexp.last_match(1)
    i += 1
  when '--dry-run', '-n'
    dry_run = true
    i += 1
  when '--help', '-h'
    puts 'Usage: ruby line_break.rb <file.adoc> [-o output.adoc] [--dry-run]'
    puts ''
    puts 'Options:'
    puts '  -o FILE     Write output to FILE (default: overwrite input)'
    puts '  --dry-run   Show what would be changed without modifying files'
    exit 0
  else
    input_file = arg
    i += 1
  end
end

if input_file.nil?
  puts 'Usage: ruby line_break.rb <file.adoc> [-o output.adoc] [--dry-run]'
  puts ''
  puts 'Options:'
  puts '  -o FILE     Write output to FILE (default: overwrite input)'
  puts '  --dry-run   Show what would be changed without modifying files'
  exit 1
end

unless File.exist?(input_file)
  puts "Error: File not found: #{input_file}"
  exit 1
end

result = process_file(input_file)

if result[:count].zero?
  puts "#{input_file}: No hard line breaks found"
  exit 0
end

if dry_run
  puts "#{input_file}: Would remove #{result[:count]} hard line break(s)"
  exit 0
end

output_file ||= input_file

tmp = Tempfile.new(['adoc', '.adoc'], File.dirname(output_file))
tmp.write(result[:lines].join("\n") + "\n")
tmp.close
FileUtils.mv(tmp.path, output_file)

puts "#{output_file}: Removed #{result[:count]} hard line break(s)"
