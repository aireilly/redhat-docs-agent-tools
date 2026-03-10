#!/usr/bin/env ruby
# frozen_string_literal: true

# task_contents.rb
# Adds missing .Procedure block title to procedure modules for DITA compatibility.
# Usage: ruby task_contents.rb <file.adoc> [-o output.adoc] [--dry-run]

require 'tempfile'
require 'fileutils'

class TaskContentsFixer
  PATTERNS = {
    content_type_procedure: /^:_(?:mod-docs-)?content-type:\s*(?i:procedure)\s*$/,
    procedure_title: /^\.{1,2}Procedure\s*$/,
    prerequisites_title: /^\.{1,2}Prerequisites?\s*$/,
    verification_title: /^\.{1,2}(?:Verification|Results?|Troubleshooting|Next steps?|Additional resources)\s*$/i,
    ordered_list: /^\s*\.\s+\S/,
    unordered_list: /^\s*[\*-]\s+/,
    comment_block: %r{^/{4,}\s*$},
    comment_line: %r{^//($|[^/].*)$},
    code_block: /^(\.{4,}|-{4,})\s*$/,
    empty_line: /^\s*$/,
    block_title: /^\.{1,2}[A-Za-z]/,
    attribute_list: /^\[.*\]\s*$/
  }.freeze

  def initialize(dry_run: false)
    @dry_run = dry_run
  end

  def process_file(file_path)
    content = File.read(file_path, encoding: 'UTF-8')
    lines = content.lines.map(&:chomp)

    # Check if this is a procedure module
    unless procedure_module?(lines)
      puts "#{file_path}: Not a procedure module (skipped)"
      return
    end

    # Check if .Procedure already exists
    if has_procedure_title?(lines)
      puts "#{file_path}: .Procedure title already exists"
      return
    end

    # Find where to insert .Procedure
    insert_line = find_procedure_insert_point(lines)

    if insert_line.nil?
      puts "#{file_path}: No ordered list found for procedure steps"
      return
    end

    if @dry_run
      puts "#{file_path}: Would add .Procedure title before line #{insert_line + 1}"
      return
    end

    # Insert .Procedure title
    lines.insert(insert_line, '.Procedure')
    lines.insert(insert_line, '')

    # Write the updated content
    File.write(file_path, lines.join("\n") + "\n")
    puts "#{file_path}: Added .Procedure title before line #{insert_line + 1}"
  end

  private

  def procedure_module?(lines)
    lines.any? { |line| line.match?(PATTERNS[:content_type_procedure]) }
  end

  def has_procedure_title?(lines)
    in_comment_block = false
    comment_delimiter = nil
    in_code_block = false
    code_delimiter = nil

    lines.each do |line|
      # Track comment blocks
      if line.match?(PATTERNS[:comment_block])
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

      # Track code blocks
      if line.match?(PATTERNS[:code_block])
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

      return true if line.match?(PATTERNS[:procedure_title])
    end

    false
  end

  def find_procedure_insert_point(lines)
    in_comment_block = false
    comment_delimiter = nil
    in_code_block = false
    code_delimiter = nil
    past_prerequisites = false
    in_prerequisites = false

    lines.each_with_index do |line, index|
      # Track comment blocks
      if line.match?(PATTERNS[:comment_block])
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
      next if line.match?(PATTERNS[:comment_line])

      # Track code blocks
      if line.match?(PATTERNS[:code_block])
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

      # Track Prerequisites section
      if line.match?(PATTERNS[:prerequisites_title])
        in_prerequisites = true
        next
      end

      # Check if we've hit a verification or other section (past procedure area)
      if line.match?(PATTERNS[:verification_title])
        # If we hit verification without finding steps, no insert needed
        return nil
      end

      # When in prerequisites, look for the end
      if in_prerequisites
        # Prerequisites ends when we hit another block title or empty line followed by ordered list
        if line.match?(PATTERNS[:block_title]) && !line.match?(PATTERNS[:prerequisites_title])
          in_prerequisites = false
          past_prerequisites = true
        elsif line.match?(PATTERNS[:empty_line])
          # Check if next non-empty line is an ordered list
          next_index = index + 1
          while next_index < lines.length && lines[next_index].match?(PATTERNS[:empty_line])
            next_index += 1
          end
          if next_index < lines.length && lines[next_index].match?(PATTERNS[:ordered_list])
            in_prerequisites = false
            past_prerequisites = true
          end
        end
        next
      end

      # Look for the first ordered list that starts procedure steps
      if line.match?(PATTERNS[:ordered_list])
        # Insert before this line (and before any preceding empty line)
        insert_point = index
        while insert_point > 0 && lines[insert_point - 1].match?(PATTERNS[:empty_line])
          insert_point -= 1
        end
        # Keep one empty line before .Procedure
        return insert_point
      end
    end

    nil
  end
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
    puts 'Usage: ruby task_contents.rb <file.adoc> [-o output.adoc] [--dry-run]'
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
  puts 'Usage: ruby task_contents.rb <file.adoc> [-o output.adoc] [--dry-run]'
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

fixer = TaskContentsFixer.new(dry_run: dry_run)
fixer.process_file(input_file)
