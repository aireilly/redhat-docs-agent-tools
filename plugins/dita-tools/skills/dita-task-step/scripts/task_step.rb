#!/usr/bin/env ruby
# frozen_string_literal: true

# task_step.rb
# Fixes list continuations in procedure steps for DITA compatibility.
# Usage: ruby task_step.rb <file.adoc> [-o output.adoc] [--dry-run]

require 'tempfile'
require 'fileutils'

class TaskStepFixer
  PATTERNS = {
    content_type_procedure: /^:_(?:mod-docs-)?content-type:\s*(?i:procedure)\s*$/,
    procedure_title: /^\.{1,2}Procedure\s*$/,
    supported_title: /^\.{1,2}(?:Prerequisites?|Procedure|Verification|Results?|Troubleshooting|Next steps?|Additional resources)\s*$/i,
    block_title: /^\.{1,2}[A-Za-z]/,
    ordered_list: /^(\s*)\.+\s+(.+)$/,
    unordered_list: /^(\s*)[\*-]\s+(.+)$/,
    description_list: /^(\s*)\S.*?:{2,4}(?:\s+.*)?$/,
    list_continue: /^\+\s*$/,
    comment_block: %r{^/{4,}\s*$},
    comment_line: %r{^//($|[^/].*)$},
    code_block_start: /^(\[source[^\]]*\]|\[listing[^\]]*\]|\[literal[^\]]*\])$/,
    block_delimiter: /^(\.{4,}|-{4,}|={4,}|\+{4,}|_{4,}|\*{4,}|--)\s*$/,
    admonition: /^\[(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*$/,
    attribute_list: /^\[.*\]\s*$/,
    empty_line: /^\s*$/,
    paragraph: /^\S/,
    example_block: /^={4,}\s*$/,
    table_delimiter: /^\|={3,}\s*$/,
    table_cell: /^\|/,
    conditional: /^(?:ifdef|ifndef|endif|ifeval):{1,2}/
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

    result = fix_list_continuations(lines)

    if result[:added_count].zero?
      puts "#{file_path}: No missing list continuations found"
      return
    end

    if @dry_run
      puts "#{file_path}: Would add #{result[:added_count]} list continuation(s)"
      result[:locations].each do |loc|
        puts "  Line #{loc}: Would add + continuation marker"
      end
      return
    end

    # Write the updated content
    File.write(file_path, result[:lines].join("\n") + "\n")
    puts "#{file_path}: Added #{result[:added_count]} list continuation(s)"
  end

  private

  def procedure_module?(lines)
    lines.any? { |line| line.match?(PATTERNS[:content_type_procedure]) }
  end

  def fix_list_continuations(lines)
    in_comment_block = false
    comment_delimiter = nil
    in_code_block = false
    code_delimiter = nil
    in_table = false
    in_procedure = false
    in_step = false
    after_empty_line = false
    last_step_indent = ''

    new_lines = []
    added_count = 0
    locations = []

    i = 0
    while i < lines.length
      line = lines[i]

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
        i += 1
        next
      end

      if in_comment_block
        new_lines << line
        i += 1
        next
      end

      # Track block delimiters (code blocks, example blocks, etc.)
      if line.match?(PATTERNS[:block_delimiter])
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
        after_empty_line = false
        i += 1
        next
      end

      if in_code_block
        new_lines << line
        i += 1
        next
      end

      # Track table blocks
      if line.match?(PATTERNS[:table_delimiter])
        in_table = !in_table
        new_lines << line
        i += 1
        next
      end

      if in_table
        new_lines << line
        i += 1
        next
      end

      # Check for Procedure section
      if line.match?(PATTERNS[:procedure_title])
        in_procedure = true
        in_step = false
        new_lines << line
        i += 1
        next
      end

      # Check for other supported sections (exit procedure)
      if in_procedure && line.match?(PATTERNS[:supported_title]) &&
         !line.match?(PATTERNS[:procedure_title])
        in_procedure = false
        in_step = false
      end

      unless in_procedure
        new_lines << line
        i += 1
        next
      end

      # Track empty lines
      if line.match?(PATTERNS[:empty_line])
        after_empty_line = true if in_step
        new_lines << line
        i += 1
        next
      end

      # Check for list continuation marker
      if line.match?(PATTERNS[:list_continue])
        after_empty_line = false
        new_lines << line
        i += 1
        next
      end

      # Check for ordered list item (step)
      match = line.match(PATTERNS[:ordered_list])
      if match
        in_step = true
        last_step_indent = match[1]
        after_empty_line = false
        new_lines << line
        i += 1
        next
      end

      # Check for unordered list or description list (sub-items)
      if line.match?(PATTERNS[:unordered_list]) || line.match?(PATTERNS[:description_list])
        after_empty_line = false
        new_lines << line
        i += 1
        next
      end

      # If we're in a step and there was an empty line, we need continuation
      if in_step && after_empty_line
        # Check if this is content that needs continuation
        if needs_continuation?(line)
          # Insert continuation marker before this line
          # Find where to insert (after the last empty line)
          insert_idx = new_lines.length
          while insert_idx > 0 && new_lines[insert_idx - 1].match?(PATTERNS[:empty_line])
            insert_idx -= 1
          end

          # Only add if there isn't already a continuation marker
          unless new_lines[insert_idx - 1]&.match?(PATTERNS[:list_continue])
            new_lines.insert(insert_idx, '+')
            added_count += 1
            locations << i + 1
          end
        end
        after_empty_line = false
      end

      # Check for block title (might end the step context)
      if line.match?(PATTERNS[:block_title]) && !line.match?(PATTERNS[:supported_title])
        # Block title within step, needs continuation if after empty
        after_empty_line = false
      end

      new_lines << line
      i += 1
    end

    { lines: new_lines, added_count: added_count, locations: locations }
  end

  def needs_continuation?(line)
    # Exclude content that should NOT trigger continuation
    return false if line.match?(PATTERNS[:table_cell])        # Table cells
    return false if line.match?(PATTERNS[:table_delimiter])   # Table delimiters
    return false if line.match?(PATTERNS[:conditional])       # ifdef/ifndef/endif/ifeval
    return false if line.match?(PATTERNS[:ordered_list])      # Ordered list items (nested steps)
    return false if line.match?(PATTERNS[:unordered_list])    # Unordered list items
    return false if line.match?(PATTERNS[:description_list])  # Definition list items
    return false if line.match?(PATTERNS[:list_continue])     # Already has continuation
    return false if line.match?(/^--\s*$/)                    # Open block delimiter

    # Content that typically needs to be attached to the preceding step
    return true if line.match?(PATTERNS[:code_block_start])
    return true if line.match?(PATTERNS[:admonition])
    return true if line.match?(PATTERNS[:attribute_list])
    return true if line.match?(PATTERNS[:block_delimiter])
    return true if line.match?(PATTERNS[:paragraph])

    false
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
    puts 'Usage: ruby task_step.rb <file.adoc> [-o output.adoc] [--dry-run]'
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
  puts 'Usage: ruby task_step.rb <file.adoc> [-o output.adoc] [--dry-run]'
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

fixer = TaskStepFixer.new(dry_run: dry_run)
fixer.process_file(input_file)
