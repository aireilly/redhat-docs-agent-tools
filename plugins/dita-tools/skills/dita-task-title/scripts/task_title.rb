#!/usr/bin/env ruby
# frozen_string_literal: true

# task_title.rb
# Removes unsupported block titles from procedure modules for DITA compatibility.
# Usage: ruby task_title.rb <file.adoc> [-o output.adoc] [--dry-run]

require 'tempfile'
require 'fileutils'

class TaskTitleFixer
  PATTERNS = {
    content_type_procedure: /^:_(?:mod-docs-)?content-type:\s*(?i:procedure)\s*$/,
    supported_title: /^\.{1,2}(?:Prerequisites?|Procedure|Verification|Results?|Troubleshooting|Troubleshooting steps?|Next steps?|Additional resources)\s*$/i,
    block_title: /^\.{1,2}([A-Za-z][^\n]*?)\s*$/,
    table_cell: /^\.[^\s\|]+\|/,
    comment_block: %r{^/{4,}\s*$},
    comment_line: %r{^//($|[^/].*)$},
    code_block: /^(\.{4,}|-{4,})\s*$/,
    list_continue: /^\+\s*$/,
    empty_line: /^\s*$/,
    image: /^image::/,
    table: /^\|={3,}\s*$/,
    example_block: /^\[example\]\s*$/i,
    example_delim: /^={4,}\s*$/
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

    result = remove_unsupported_titles(lines)

    if result[:removed_count].zero?
      puts "#{file_path}: No unsupported titles found"
      return
    end

    if @dry_run
      puts "#{file_path}: Would remove #{result[:removed_count]} unsupported title(s)"
      result[:removed_titles].each do |item|
        puts "  Line #{item[:line]}: #{item[:title]}"
      end
      return
    end

    # Write the updated content
    File.write(file_path, result[:lines].join("\n") + "\n")
    puts "#{file_path}: Removed #{result[:removed_count]} unsupported title(s)"
    result[:removed_titles].each do |item|
      puts "  Line #{item[:line]}: #{item[:title]}"
    end
  end

  private

  def procedure_module?(lines)
    lines.any? { |line| line.match?(PATTERNS[:content_type_procedure]) }
  end

  def remove_unsupported_titles(lines)
    in_comment_block = false
    comment_delimiter = nil
    in_code_block = false
    code_delimiter = nil
    is_list_continue = false
    expect_block = false

    new_lines = []
    removed_count = 0
    removed_titles = []

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
        new_lines << line
        next
      end

      if in_comment_block
        new_lines << line
        next
      end

      # Skip single-line comments
      if line.match?(PATTERNS[:comment_line])
        new_lines << line
        next
      end

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
        new_lines << line
        expect_block = false
        is_list_continue = false
        next
      end

      if in_code_block
        new_lines << line
        next
      end

      # Track list continuation
      if line.match?(PATTERNS[:list_continue])
        is_list_continue = true
        new_lines << line
        next
      end

      # Check for table, image, example - these reset expect_block
      if line.match?(PATTERNS[:table]) || line.match?(PATTERNS[:image]) ||
         line.match?(PATTERNS[:example_block]) || line.match?(PATTERNS[:example_delim])
        expect_block = false
        is_list_continue = false
        new_lines << line
        next
      end

      # Check for block title
      if line.match?(PATTERNS[:block_title]) && !line.match?(PATTERNS[:table_cell])
        if line.match?(PATTERNS[:supported_title])
          # Supported title - keep it
          new_lines << line
        elsif is_list_continue
          # Title after list continuation - keep it (it's a block title for step content)
          new_lines << line
        else
          # Unsupported title - mark for potential removal
          expect_block = { line: line, index: index + 1 }
        end
        is_list_continue = false
        next
      end

      # If we had a pending unsupported title, now we know it's not followed by special block
      if expect_block
        # Remove the title (don't add it to new_lines)
        removed_count += 1
        removed_titles << { line: expect_block[:index], title: expect_block[:line] }
        expect_block = false
      end

      is_list_continue = false
      new_lines << line
    end

    # Handle case where file ends with unsupported title
    if expect_block
      removed_count += 1
      removed_titles << { line: expect_block[:index], title: expect_block[:line] }
    end

    # Clean up consecutive empty lines
    cleaned_lines = clean_empty_lines(new_lines)

    { lines: cleaned_lines, removed_count: removed_count, removed_titles: removed_titles }
  end

  def clean_empty_lines(lines)
    result = []
    empty_count = 0

    lines.each do |line|
      if line.strip.empty?
        empty_count += 1
        result << line if empty_count <= 2
      else
        empty_count = 0
        result << line
      end
    end

    result
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
    puts 'Usage: ruby task_title.rb <file.adoc> [-o output.adoc] [--dry-run]'
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
  puts 'Usage: ruby task_title.rb <file.adoc> [-o output.adoc] [--dry-run]'
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

fixer = TaskTitleFixer.new(dry_run: dry_run)
fixer.process_file(input_file)
