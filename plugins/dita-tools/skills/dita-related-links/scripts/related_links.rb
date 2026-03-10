#!/usr/bin/env ruby
# frozen_string_literal: true

# related_links.rb
# Removes non-link content from Additional resources sections for DITA compatibility.
# Usage: ruby related_links.rb <file.adoc> [-o output.adoc] [--dry-run]

require 'tempfile'
require 'fileutils'

class RelatedLinksCleaner
  PATTERNS = {
    additional_resources: /^(?:={2,}\s+|\.{1,2})Additional resources\s*$/i,
    role_additional: /^\[role=['"]?_additional-resources['"]?\]\s*$/,
    any_title: /^(?:={2,}\s+|\.{1,2})(?!\s*$).+$/,
    comment_block: %r{^/{4,}\s*$},
    comment_line: %r{^//($|[^/].*)$},
    empty_line: /^\s*$/,
    attribute_def: /^:!?\S[^:]*:/,
    conditional: /^(?:ifn?def|ifeval|endif)::\S*\[.*\]\s*$/,
    include: /^include::(?:[^\s\[]+)\[.*\]\s*$/,
    id_attribute: /^\[(?:id=['"]|#|\[)/,
    # Valid link patterns - allow trailing text after link (will be stripped during normalization)
    link_macro: /^\s*[\*-]\s+(?:link|mailto):(?:[^\s\[]*)\[.*?\]/,
    inline_link: /^\s*[\*-]\s+(?:|link:|<)(?:|\+\+)(?:https?|file|ftp|irc):\/\/[^\s\[\]]+(?:|\+\+)(?:|\[.*?\])>?/,
    # Bare URL with link text (needs correction to link: macro)
    bare_url_with_text: /^\s*[\*-]\s+(https?:\/\/[^\s\[\]]+)\[([^\]]+)\](.*)$/,
    xref_macro: /^\s*[\*-]\s+xref:[A-Za-z0-9\/.:{].*?\[.*?\]/,
    inline_xref: /^\s*[\*-]\s+<<[A-Za-z0-9\/.:{].*?>>/,
    attribute_ref_link: /^\s*[\*-]\s+\{(?:[0-9A-Za-z_][0-9A-Za-z_-]*|set:.+?|counter2?:.+?)\}(?:|[^\[\s]*\[.*?\])/,
    list_item: /^\s*[\*-]\s+/,
    # Paragraph-style links (not list items) - these contain links but start with text
    para_link_macro: /^[^*\-\s].*(?:link|mailto):(?:[^\s\[]*)\[.*?\]/,
    para_xref: /^[^*\-\s].*(?:xref:[^\[]*\[.*?\]|<<[^>]+>>)/
  }.freeze

  def initialize(dry_run: false)
    @dry_run = dry_run
  end

  def process_file(file_path)
    content = File.read(file_path, encoding: 'UTF-8')
    lines = content.lines.map(&:chomp)

    result = clean_additional_resources(lines)

    if result[:removed_count].zero? && result[:normalized_count].zero?
      if result[:has_additional_resources]
        puts "#{file_path}: No issues found in Additional resources"
      else
        puts "#{file_path}: No Additional resources section found"
      end
      return
    end

    if @dry_run
      if result[:removed_count].positive?
        puts "#{file_path}: Would remove #{result[:removed_count]} non-link item(s) from Additional resources"
        result[:removed_items].each do |item|
          puts "  Line #{item[:line]}: #{item[:content][0..60]}..."
        end
      end
      if result[:normalized_count].positive?
        puts "#{file_path}: Would normalize #{result[:normalized_count]} link(s) in Additional resources"
        result[:normalized_items].each do |item|
          puts "  Line #{item[:line]}:"
          puts "    From: #{item[:original].strip}"
          puts "    To:   #{item[:normalized].strip}"
        end
      end
      return
    end

    # Write the cleaned content
    output_content = result[:lines].join("\n") + "\n"
    File.write(file_path, output_content)

    messages = []
    messages << "removed #{result[:removed_count]} non-link item(s)" if result[:removed_count].positive?
    messages << "normalized #{result[:normalized_count]} link(s)" if result[:normalized_count].positive?
    puts "#{file_path}: #{messages.join(', ')} in Additional resources"
  end

  private

  def clean_additional_resources(lines)
    in_comment_block = false
    comment_delimiter = nil
    in_additional_resources = false
    has_additional_resources = false

    removed_count = 0
    removed_items = []
    normalized_count = 0
    normalized_items = []
    cleaned_lines = []
    skip_next_if_empty = false

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
        cleaned_lines << line
        next
      end

      if in_comment_block
        cleaned_lines << line
        next
      end

      # Skip single-line comments
      if line.match?(PATTERNS[:comment_line])
        cleaned_lines << line
        next
      end

      # Check for Additional resources section
      if line.match?(PATTERNS[:additional_resources]) || line.match?(PATTERNS[:role_additional])
        in_additional_resources = true
        has_additional_resources = true
        cleaned_lines << line
        next
      end

      # Check if we've left the Additional resources section
      if in_additional_resources && line.match?(PATTERNS[:any_title]) &&
         !line.match?(PATTERNS[:additional_resources])
        in_additional_resources = false
      end

      unless in_additional_resources
        cleaned_lines << line
        next
      end

      # Inside Additional resources - check what to keep

      # Always keep empty lines, attributes, conditionals, includes
      if line.match?(PATTERNS[:empty_line]) ||
         line.match?(PATTERNS[:attribute_def]) ||
         line.match?(PATTERNS[:conditional]) ||
         line.match?(PATTERNS[:include]) ||
         line.match?(PATTERNS[:id_attribute])
        # Skip empty line if previous item was removed
        if skip_next_if_empty && line.match?(PATTERNS[:empty_line])
          skip_next_if_empty = false
          next
        end
        cleaned_lines << line
        next
      end

      skip_next_if_empty = false

      # Check if this is a valid link item
      if valid_link_item?(line)
        # Normalize the link item to fix common AsciiDoc issues
        normalized_line = normalize_link_item(line)
        if normalized_line != line
          normalized_count += 1
          normalized_items << { line: index + 1, original: line, normalized: normalized_line }
        end
        cleaned_lines << normalized_line
        next
      end

      # This is non-link content - remove it
      removed_count += 1
      removed_items << { line: index + 1, content: line }
      skip_next_if_empty = true
    end

    # Clean up consecutive empty lines
    cleaned_lines = clean_empty_lines(cleaned_lines)

    {
      lines: cleaned_lines,
      removed_count: removed_count,
      removed_items: removed_items,
      normalized_count: normalized_count,
      normalized_items: normalized_items,
      has_additional_resources: has_additional_resources
    }
  end

  def valid_link_item?(line)
    # Check if it's a list item with a valid link
    return true if line.match?(PATTERNS[:link_macro])
    return true if line.match?(PATTERNS[:inline_link])
    return true if line.match?(PATTERNS[:xref_macro])
    return true if line.match?(PATTERNS[:inline_xref])
    return true if line.match?(PATTERNS[:attribute_ref_link])
    # Bare URL with link text is valid but needs normalization
    return true if line.match?(PATTERNS[:bare_url_with_text])
    # Paragraph-style links (will be converted to list items during normalization)
    return true if line.match?(PATTERNS[:para_link_macro])
    return true if line.match?(PATTERNS[:para_xref])

    false
  end

  def normalize_link_item(line)
    normalized = line.dup

    # Convert paragraph-style links to list items
    # e.g., "See also link:url[text]." -> "* link:url[text]"
    if normalized =~ /^[^*\-\s].*?((?:link|mailto):[^\s\[]*\[[^\]]*\])/
      link_part = Regexp.last_match(1)
      normalized = "* #{link_part}"
    elsif normalized =~ /^[^*\-\s].*?(xref:[^\[]*\[[^\]]*\])/
      xref_part = Regexp.last_match(1)
      normalized = "* #{xref_part}"
    elsif normalized =~ /^[^*\-\s].*?(<<[^>]+>>)/
      xref_part = Regexp.last_match(1)
      normalized = "* #{xref_part}"
    end

    # Fix bare URLs with link text: https://url[Text] trailing text -> link:https://url[Text]
    # This pattern captures: * https://url[Link Text] in the Foo documentation
    if normalized =~ /^(\s*[\*-]\s+)(https?:\/\/[^\s\[\]]+)\[([^\]]+)\].*$/
      prefix = Regexp.last_match(1)
      url = Regexp.last_match(2)
      link_text = Regexp.last_match(3).strip
      # Remove trailing period from link text
      link_text = link_text.sub(/\.\s*$/, '')
      normalized = "#{prefix}link:#{url}[#{link_text}]"
    end

    # Strip trailing text after link macro: * link:url[Text] in the docs -> * link:url[Text]
    if normalized =~ /^(\s*[\*-]\s+(?:link|mailto):[^\[]*\[[^\]]*\])(?:\s+.+|\.\s*)$/
      normalized = Regexp.last_match(1)
    end

    # Strip trailing text after xref: * xref:file[Text] for more info -> * xref:file[Text]
    if normalized =~ /^(\s*[\*-]\s+xref:[^\[]*\[[^\]]*\])(?:\s+.+|\.\s*)$/
      normalized = Regexp.last_match(1)
    end

    # Strip trailing text after inline xref: * <<target>> for details -> * <<target>>
    if normalized =~ /^(\s*[\*-]\s+<<[^>]+>>)(?:\s+.+|\.\s*)$/
      normalized = Regexp.last_match(1)
    end

    # Fix trailing period inside link text: link:url[Text.] -> link:url[Text]
    if normalized =~ /^(\s*[\*-]\s+(?:link|mailto):[^\[]*\[[^\]]*)\.\](\s*)$/
      normalized = "#{Regexp.last_match(1)}]#{Regexp.last_match(2)}"
    end

    # Fix xref trailing period inside: xref:file[Text.] -> xref:file[Text]
    if normalized =~ /^(\s*[\*-]\s+xref:[^\[]*\[[^\]]*)\.\](\s*)$/
      normalized = "#{Regexp.last_match(1)}]#{Regexp.last_match(2)}"
    end

    normalized
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
    puts 'Usage: ruby related_links.rb <file.adoc> [-o output.adoc] [--dry-run]'
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
  puts 'Usage: ruby related_links.rb <file.adoc> [-o output.adoc] [--dry-run]'
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

cleaner = RelatedLinksCleaner.new(dry_run: dry_run)
cleaner.process_file(input_file)
