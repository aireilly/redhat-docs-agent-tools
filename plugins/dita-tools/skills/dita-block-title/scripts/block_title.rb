#!/usr/bin/env ruby
# frozen_string_literal: true

# block_title.rb
# Fixes unsupported block titles in AsciiDoc files for DITA compatibility.
# Block titles are only valid for examples, figures (images), and tables.
# Usage: ruby block_title.rb <file.adoc> [-o output.adoc] [--dry-run]

require 'fileutils'

class BlockTitleFixer
  PATTERNS = {
    # Block title patterns
    block_title: /^\.([A-Za-z][^\n]*?)\s*$/,
    double_dot_title: /^\.\.([A-Za-z][^\n]*?)\s*$/,

    # Valid block title targets (DITA-compatible)
    image: /^image::/,
    table_start: /^\|={3,}\s*$/,
    example_block: /^\[example\]\s*$/i,
    example_delim: /^={4,}\s*$/,

    # Source/code blocks (need remediation)
    source_block: /^\[source[,\]]?/i,
    listing_block: /^\[listing\]/i,
    code_delim: /^-{4,}\s*$/,
    literal_delim: /^\.{4,}\s*$/,

    # Procedure-specific titles (handled by dita-task-title)
    procedure_title: /^\.{1,2}(?:Prerequisites?|Procedure|Verification|Results?|Troubleshooting|Troubleshooting steps?|Next steps?|Additional resources)\s*$/i,

    # Context patterns
    comment_block: %r{^/{4,}\s*$},
    comment_line: %r{^//($|[^/].*)$},
    list_continue: /^\+\s*$/,
    ordered_list_item: /^\.\s+\S/,
    unordered_list_item: /^\*+\s+\S/,
    definition_list: /^.+::(\s|$)/,
    empty_line: /^\s*$/,
    attribute: /^\[.*\]\s*$/,
    section_heading: /^=+\s+\S/,

    # Patterns indicating preceding step context
    step_context_end: /^(\.\s+|\*+\s+|::)/,

    # Redundant title patterns (often redundant with preceding text)
    redundant_prefix: /^(?:example|sample)\s+/i
  }.freeze

  def initialize(dry_run: false)
    @dry_run = dry_run
  end

  def process_file(file_path, output_path = nil)
    content = File.read(file_path, encoding: 'UTF-8')
    lines = content.lines.map(&:chomp)

    result = fix_block_titles(lines)

    if result[:fixed_count].zero?
      puts "#{file_path}: No unsupported block titles found"
      return
    end

    if @dry_run
      puts "#{file_path}: Would fix #{result[:fixed_count]} block title(s)"
      result[:fixes].each do |fix|
        puts "  Line #{fix[:line]}: #{fix[:description]}"
      end
      return
    end

    output = output_path || file_path
    File.write(output, result[:lines].join("\n") + "\n")
    puts "#{file_path}: Fixed #{result[:fixed_count]} block title(s)"
    result[:fixes].each do |fix|
      puts "  Line #{fix[:line]}: #{fix[:description]}"
    end
  end

  private

  def fix_block_titles(lines)
    in_comment_block = false
    comment_delimiter = nil
    in_code_block = false
    code_delimiter = nil
    in_list_context = false
    after_list_continue = false

    new_lines = []
    fixed_count = 0
    fixes = []
    skip_next = false

    lines.each_with_index do |line, index|
      if skip_next
        skip_next = false
        new_lines << line
        next
      end

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
      if line.match?(PATTERNS[:code_delim]) || line.match?(PATTERNS[:literal_delim])
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
        after_list_continue = false
        next
      end

      if in_code_block
        new_lines << line
        next
      end

      # Track list context
      if line.match?(PATTERNS[:ordered_list_item]) || line.match?(PATTERNS[:unordered_list_item])
        in_list_context = true
        after_list_continue = false
        new_lines << line
        next
      end

      # Track list continuation
      if line.match?(PATTERNS[:list_continue])
        after_list_continue = true
        new_lines << line
        next
      end

      # Reset list context on empty lines after non-continued content
      if line.match?(PATTERNS[:empty_line])
        # Keep tracking - don't reset yet
        new_lines << line
        next
      end

      # Check for section headings - reset list context
      if line.match?(PATTERNS[:section_heading])
        in_list_context = false
        after_list_continue = false
        new_lines << line
        next
      end

      # Check for block title
      title_match = line.match(PATTERNS[:block_title]) || line.match(PATTERNS[:double_dot_title])
      if title_match
        title_text = title_match[1]

        # Skip procedure-specific titles (handled by dita-task-title)
        if line.match?(PATTERNS[:procedure_title])
          new_lines << line
          after_list_continue = false
          next
        end

        # Look ahead to see what follows
        next_content_index, next_content_line = find_next_content(lines, index)

        if next_content_line.nil?
          # Title at end of file - remove it
          fixed_count += 1
          fixes << { line: index + 1, description: "\"#{line}\" -> removed (end of file)" }
          after_list_continue = false
          next
        end

        # Check if followed by valid DITA block title target
        if valid_block_title_target?(lines, next_content_index)
          new_lines << line
          after_list_continue = false
          next
        end

        # Remediate the block title
        remediation = determine_remediation(title_text, lines, index, next_content_index, after_list_continue, in_list_context)

        case remediation[:action]
        when :convert_with_continuation
          # Convert to inline text with colon and add list continuation
          new_lines << "#{title_text}:"
          new_lines << '+'
          fixed_count += 1
          fixes << { line: index + 1, description: "\"#{line}\" -> \"#{title_text}:\" (before source block)" }

        when :convert_inline
          # Convert to inline text with colon
          new_lines << "#{title_text}:"
          fixed_count += 1
          fixes << { line: index + 1, description: "\"#{line}\" -> \"#{title_text}:\"" }

        when :convert_to_deflist
          # Convert to definition list term
          new_lines << "#{title_text}::"
          fixed_count += 1
          fixes << { line: index + 1, description: "\"#{line}\" -> \"#{title_text}::\" (definition list)" }

        when :remove
          # Remove the block title entirely
          fixed_count += 1
          fixes << { line: index + 1, description: "\"#{line}\" -> removed (redundant)" }
          # Don't add anything to new_lines

        else
          # Default: convert to inline text
          new_lines << "#{title_text}:"
          fixed_count += 1
          fixes << { line: index + 1, description: "\"#{line}\" -> \"#{title_text}:\"" }
        end

        after_list_continue = false
        next
      end

      # Regular line
      after_list_continue = false
      new_lines << line
    end

    # Clean up any doubled empty lines that might result from removals
    cleaned_lines = clean_empty_lines(new_lines)

    { lines: cleaned_lines, fixed_count: fixed_count, fixes: fixes }
  end

  def find_next_content(lines, current_index)
    (current_index + 1...lines.length).each do |i|
      line = lines[i]
      # Skip empty lines and attributes
      next if line.match?(PATTERNS[:empty_line])
      next if line.match?(PATTERNS[:attribute]) && !line.match?(PATTERNS[:source_block])

      return [i, line]
    end
    [nil, nil]
  end

  def valid_block_title_target?(lines, next_index)
    return false if next_index.nil?

    line = lines[next_index]

    # Valid targets: image, table, example block
    return true if line.match?(PATTERNS[:image])
    return true if line.match?(PATTERNS[:table_start])
    return true if line.match?(PATTERNS[:example_block])
    return true if line.match?(PATTERNS[:example_delim])

    # Check if it's an attribute followed by a valid target
    if line.match?(PATTERNS[:attribute]) && !line.match?(PATTERNS[:source_block])
      next_next_index, next_next_line = find_next_content(lines, next_index)
      return valid_block_title_target?(lines, next_next_index) if next_next_line
    end

    false
  end

  def determine_remediation(title_text, lines, title_index, next_content_index, after_list_continue, in_list_context)
    return { action: :remove } if next_content_index.nil?

    next_line = lines[next_content_index]

    # Check if followed by source block
    is_source_block = next_line.match?(PATTERNS[:source_block]) ||
                      next_line.match?(PATTERNS[:listing_block]) ||
                      next_line.match?(PATTERNS[:code_delim])

    # Check if the title looks redundant (e.g., "Example output" before a source block)
    is_redundant = redundant_title?(title_text, lines, title_index)

    if is_redundant
      return { action: :remove }
    end

    if is_source_block
      if after_list_continue
        # Already has continuation before title, no need to add another
        return { action: :convert_inline }
      else
        return { action: :convert_with_continuation }
      end
    end

    # Check if followed by a paragraph (might be a section-like title)
    is_paragraph = !next_line.match?(PATTERNS[:ordered_list_item]) &&
                   !next_line.match?(PATTERNS[:unordered_list_item]) &&
                   !next_line.match?(PATTERNS[:definition_list]) &&
                   !next_line.match?(PATTERNS[:attribute]) &&
                   !next_line.match?(PATTERNS[:section_heading]) &&
                   next_line.length > 50 # Longer text suggests paragraph

    # If it looks like a section heading (title followed by substantial paragraph)
    if is_paragraph && looks_like_section_title?(title_text)
      return { action: :convert_to_deflist }
    end

    # Default: convert to inline text with colon
    { action: :convert_inline }
  end

  def redundant_title?(title_text, lines, title_index)
    # Check if preceding text already indicates an example, making the title redundant
    # Only remove titles when there's EXPLICIT redundancy with preceding text

    # Check if preceding non-empty line ends with "example:" or "For example:" or similar
    (title_index - 1).downto([0, title_index - 5].max) do |i|
      prev_line = lines[i]
      next if prev_line.match?(PATTERNS[:empty_line])

      # If previous line ends with "For example:" or similar, title is redundant
      return true if prev_line.match?(/(?:for\s+)?example:\s*$/i)
      return true if prev_line.match?(/as\s+follows:\s*$/i)
      return true if prev_line.match?(/shown\s+(?:below|here):\s*$/i)
      return true if prev_line.match?(/the\s+following\s+(?:example\s+)?shows/i)

      break
    end

    false
  end

  def looks_like_section_title?(title_text)
    # Section-like titles are typically:
    # - Capitalized
    # - Don't contain "example" or "sample"
    # - Are relatively short (under 60 chars)
    # - Don't end with punctuation other than question mark

    return false if title_text.length > 60
    return false if title_text.match?(/^(?:example|sample)\s+/i)
    return false if title_text.match?(/[.!,;:]$/)

    # Should start with capital letter
    title_text.match?(/^[A-Z]/)
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
    puts 'Usage: ruby block_title.rb <file.adoc> [-o output.adoc] [--dry-run]'
    puts ''
    puts 'Fixes unsupported block titles in AsciiDoc files for DITA compatibility.'
    puts 'Block titles can only be assigned to examples, figures, and tables in DITA.'
    puts ''
    puts 'Options:'
    puts '  -o FILE     Write output to FILE (default: overwrite input)'
    puts '  --dry-run   Show what would be changed without modifying files'
    puts '  -h, --help  Show this help message'
    exit 0
  else
    input_file = arg
    i += 1
  end
end

if input_file.nil?
  puts 'Usage: ruby block_title.rb <file.adoc> [-o output.adoc] [--dry-run]'
  puts ''
  puts 'Fixes unsupported block titles in AsciiDoc files for DITA compatibility.'
  puts 'Use --help for more information.'
  exit 1
end

unless File.exist?(input_file)
  puts "Error: File not found: #{input_file}"
  exit 1
end

fixer = BlockTitleFixer.new(dry_run: dry_run)
fixer.process_file(input_file, output_file)
