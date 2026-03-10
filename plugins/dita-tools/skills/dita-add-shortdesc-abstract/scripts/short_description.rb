#!/usr/bin/env ruby
# short_description.rb
# Adds missing [role="_abstract"] attribute for AsciiDoc files.
# Usage: ruby short_description.rb <file.adoc> [-o output.adoc] [--dry-run]

require 'tempfile'
require 'fileutils'

def process_file(path)
  content = File.read(path)
  lines = content.lines.map(&:chomp)

  # Skip ASSEMBLY and SNIPPET files - they don't need abstracts
  if content.include?(':_mod-docs-content-type: ASSEMBLY') ||
     content.include?(':_mod-docs-content-type: SNIPPET')
    return { lines: lines, modified: false, reason: 'Assembly or snippet file (skipped)' }
  end

  # Check if abstract already exists
  if content =~ /\[role=["']?_abstract["']?\]/
    return { lines: lines, modified: false, reason: 'Abstract already exists' }
  end

  in_comment_block = false
  comment_delimiter = nil
  in_code_block = false
  code_delimiter = nil
  title_line_idx = nil
  first_para_idx = nil
  found_title = false

  lines.each_with_index do |line, idx|
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
      next
    end
    next if in_comment_block

    # Skip single-line comments
    next if line =~ %r{^//($|[^/])}

    # Track code blocks
    if line =~ /^(\.{4,}|-{4,}|={4,}|\+{4,}|_{4,}|\*{4,})\s*$/
      delimiter = line.strip
      if !in_code_block
        in_code_block = true
        code_delimiter = delimiter
      elsif code_delimiter && line.strip.start_with?(code_delimiter[0]) &&
            line.strip.length >= code_delimiter.length
        in_code_block = false
        code_delimiter = nil
      end
      next
    end
    next if in_code_block

    # Check for document title (level 0 heading)
    if !found_title && line =~ /^=\s+\S.*$/
      title_line_idx = idx
      found_title = true
      next
    end

    # After title, look for first paragraph
    if found_title && first_para_idx.nil?
      # Skip empty lines
      next if line =~ /^\s*$/

      # Skip attribute definitions
      next if line =~ /^:!?\S[^:]*:/

      # Skip attribute lists (but not role="_abstract" which we want to add)
      next if line =~ /^\[(?!role)/

      # Skip conditionals
      next if line =~ /^(?:ifn?def|ifeval|endif)::/

      # Skip section titles (== or deeper)
      next if line =~ /^={2,}\s+/

      # Skip list items, includes, and other structural elements
      next if line =~ /^(\*|\d+\.|include::|image::|video::|audio::)/

      # Skip block titles (e.g., .Title of block)
      next if line =~ /^\.[A-Za-z]/

      # Skip table delimiters
      next if line =~ /^\|===?/

      # Skip admonition blocks
      next if line =~ /^\[(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]/

      # Skip table rows (lines starting with |)
      next if line =~ /^\|/

      # Skip description list items (term:: or term:::)
      next if line =~ /^.+:{2,4}\s*$/

      # Skip listing/literal block markers
      next if line =~ /^\.{2}\s*$/

      # This should be the first paragraph (text that doesn't start with special chars)
      # A valid paragraph starts with a letter, number, or certain punctuation
      if line =~ /^[A-Za-z0-9"'\(\[`_]/
        first_para_idx = idx
        break
      end
    end
  end

  # If no title found, nothing to do
  if title_line_idx.nil?
    return { lines: lines, modified: false, reason: 'No document title found' }
  end

  # If no first paragraph found after title
  if first_para_idx.nil?
    return { lines: lines, modified: false, reason: 'No paragraph found after title' }
  end

  # Insert [role="_abstract"] before the first paragraph
  lines.insert(first_para_idx, '[role="_abstract"]')

  { lines: lines, modified: true, paragraph_line: first_para_idx + 1 }
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
      puts "Error: -o requires an argument"
      exit 1
    end
  when /^-o(.+)$/
    output_file = Regexp.last_match(1)
    i += 1
  when '--dry-run', '-n'
    dry_run = true
    i += 1
  when '--help', '-h'
    puts "Usage: ruby short_description.rb <file.adoc> [-o output.adoc] [--dry-run]"
    puts ""
    puts "Options:"
    puts "  -o FILE       Write output to FILE (default: overwrite input)"
    puts "  --dry-run     Show what would be changed without modifying files"
    exit 0
  else
    input_file = arg
    i += 1
  end
end

if input_file.nil?
  puts "Usage: ruby short_description.rb <file.adoc> [-o output.adoc] [--dry-run]"
  puts ""
  puts "Options:"
  puts "  -o FILE       Write output to FILE (default: overwrite input)"
  puts "  --dry-run     Show what would be changed without modifying files"
  exit 1
end

unless File.exist?(input_file)
  puts "Error: File not found: #{input_file}"
  exit 1
end

result = process_file(input_file)

unless result[:modified]
  puts "#{input_file}: #{result[:reason]}"
  exit 0
end

if dry_run
  puts "#{input_file}: Would add [role=\"_abstract\"] before line #{result[:paragraph_line]}"
  exit 0
end

output_file ||= input_file

tmp = Tempfile.new(['adoc', '.adoc'], File.dirname(output_file))
tmp.write(result[:lines].join("\n") + "\n")
tmp.close
FileUtils.mv(tmp.path, output_file)

puts "#{output_file}: Added [role=\"_abstract\"] before line #{result[:paragraph_line]}"
