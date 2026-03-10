#!/usr/bin/env ruby
# content_type.rb
# Adds or updates :_mod-docs-content-type: attribute in AsciiDoc files.
# Detects content type from file structure, filename, folder, and content patterns.
# Usage: ruby content_type.rb <file.adoc> [-o output.adoc] [--dry-run] [--type TYPE]

require 'tempfile'
require 'fileutils'

VALID_TYPES = %w[CONCEPT PROCEDURE REFERENCE ASSEMBLY SNIPPET].freeze

# Filename prefix patterns that indicate content type
FILENAME_PREFIXES = {
  /^assembly[_-]/ => 'ASSEMBLY',
  /^con[_-]/ => 'CONCEPT',
  /^proc[_-]/ => 'PROCEDURE',
  /^ref[_-]/ => 'REFERENCE',
  /^snip[_-]/ => 'SNIPPET'
}.freeze

# Folder patterns that indicate content type
FOLDER_PATTERNS = {
  %r{/assemblies/} => 'ASSEMBLY',
  %r{/concepts/} => 'CONCEPT',
  %r{/procedures/} => 'PROCEDURE',
  %r{/references/} => 'REFERENCE',
  %r{/snippets/} => 'SNIPPET'
}.freeze

def detect_type_from_filename(path)
  basename = File.basename(path)
  FILENAME_PREFIXES.each do |pattern, type|
    return type if basename =~ pattern
  end
  nil
end

def detect_type_from_folder(path)
  abs_path = File.expand_path(path)
  FOLDER_PATTERNS.each do |pattern, type|
    return type if abs_path =~ pattern
  end
  nil
end

def detect_type_from_content(content, lines)
  # Check for .Procedure block title (strong indicator of PROCEDURE)
  if content =~ /^\.{1,2}Procedure\s*$/i
    return 'PROCEDURE'
  end

  # Check for numbered list after title (likely PROCEDURE)
  in_preamble = false
  found_title = false
  lines.each do |line|
    # Skip comment lines
    next if line =~ %r{^//}

    # Found document title
    if !found_title && line =~ /^=\s+\S/
      found_title = true
      in_preamble = true
      next
    end

    next unless in_preamble

    # Skip empty lines, attributes, conditionals
    next if line =~ /^\s*$/
    next if line =~ /^:!?\S[^:]*:/
    next if line =~ /^\[/
    next if line =~ /^(?:ifn?def|ifeval|endif)::/

    # Section heading ends preamble check
    break if line =~ /^={2,}\s+/

    # Numbered list suggests procedure
    if line =~ /^\d+\.\s+/ || line =~ /^\.{1,2}\s+\S/
      return 'PROCEDURE'
    end

    # Found regular content, stop checking
    break if line =~ /^[A-Za-z]/
  end

  # Check for tables with header rows (likely REFERENCE)
  if content =~ /^\|===/ && content =~ /^\[.*cols.*\]/
    return 'REFERENCE'
  end

  # Check for multiple include:: directives (likely ASSEMBLY)
  include_count = content.scan(/^include::/).length
  if include_count >= 2
    return 'ASSEMBLY'
  end

  nil
end

def get_existing_content_type(content)
  # Check for :_mod-docs-content-type: attribute
  if content =~ /^:_mod-docs-content-type:\s*(\S+)/
    return { attr: ':_mod-docs-content-type:', type: Regexp.last_match(1).upcase, line_pattern: /^:_mod-docs-content-type:/ }
  end
  nil
end

def get_legacy_module_type(content)
  # Check for legacy :_module-type: attribute
  if content =~ /^:_module-type:\s*(\S+)/
    return { attr: ':_module-type:', type: Regexp.last_match(1).upcase, line_pattern: /^:_module-type:/ }
  end
  nil
end

def find_insertion_point(lines)
  # Find the best place to insert the content type attribute
  # Should be at the very top, before any other content
  # But after any initial comment blocks

  in_comment_block = false
  comment_delimiter = nil
  insert_idx = 0

  lines.each_with_index do |line, idx|
    # Track comment blocks at the start
    if line =~ %r{^/{4,}\s*$}
      delimiter = line.strip
      if !in_comment_block
        in_comment_block = true
        comment_delimiter = delimiter
      elsif comment_delimiter == delimiter
        in_comment_block = false
        comment_delimiter = nil
        insert_idx = idx + 1
      end
      next
    end

    next if in_comment_block

    # Skip single-line comments at the very beginning
    if line =~ %r{^//}
      insert_idx = idx + 1
      next
    end

    # Skip empty lines at the beginning
    if line =~ /^\s*$/
      insert_idx = idx + 1
      next
    end

    # Found actual content, insert before this
    break
  end

  insert_idx
end

def process_file(path, forced_type = nil)
  content = File.read(path)
  lines = content.lines.map(&:chomp)

  # Check if :_mod-docs-content-type: already exists
  existing = get_existing_content_type(content)
  if existing
    return { lines: lines, modified: false, reason: "Already has :_mod-docs-content-type: #{existing[:type]}" }
  end

  # Check for legacy :_module-type: attribute
  legacy = get_legacy_module_type(content)
  if legacy
    # Update the attribute name
    detected_type = forced_type || legacy[:type]
    unless VALID_TYPES.include?(detected_type)
      return { lines: lines, modified: false, reason: "Invalid content type: #{detected_type}" }
    end

    # Find and replace the legacy attribute
    lines = lines.map do |line|
      if line =~ /^:_module-type:\s*/
        ":_mod-docs-content-type: #{detected_type}"
      else
        line
      end
    end

    return { lines: lines, modified: true, action: 'updated', old_attr: ':_module-type:', type: detected_type }
  end

  # Detect content type
  detected_type = forced_type
  detected_type ||= detect_type_from_filename(path)
  detected_type ||= detect_type_from_folder(path)
  detected_type ||= detect_type_from_content(content, lines)

  if detected_type.nil?
    return { lines: lines, modified: false, reason: 'Unable to determine content type (use --type to specify)' }
  end

  detected_type = detected_type.upcase
  unless VALID_TYPES.include?(detected_type)
    return { lines: lines, modified: false, reason: "Invalid content type: #{detected_type}" }
  end

  # Find insertion point
  insert_idx = find_insertion_point(lines)

  # Insert the content type attribute
  lines.insert(insert_idx, ":_mod-docs-content-type: #{detected_type}")

  { lines: lines, modified: true, action: 'added', type: detected_type, line: insert_idx + 1 }
end

# Parse command line arguments
input_file = nil
output_file = nil
dry_run = false
forced_type = nil

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
  when '--type', '-t'
    if i + 1 < ARGV.length
      forced_type = ARGV[i + 1].upcase
      unless VALID_TYPES.include?(forced_type)
        puts "Error: Invalid content type '#{forced_type}'. Valid types: #{VALID_TYPES.join(', ')}"
        exit 1
      end
      i += 2
    else
      puts "Error: --type requires an argument"
      exit 1
    end
  when /^--type=(.+)$/
    forced_type = Regexp.last_match(1).upcase
    unless VALID_TYPES.include?(forced_type)
      puts "Error: Invalid content type '#{forced_type}'. Valid types: #{VALID_TYPES.join(', ')}"
      exit 1
    end
    i += 1
  when '--dry-run', '-n'
    dry_run = true
    i += 1
  when '--help', '-h'
    puts "Usage: ruby content_type.rb <file.adoc> [-o output.adoc] [--dry-run] [--type TYPE]"
    puts ""
    puts "Adds or updates :_mod-docs-content-type: attribute in AsciiDoc files."
    puts ""
    puts "Options:"
    puts "  -o FILE       Write output to FILE (default: overwrite input)"
    puts "  --dry-run     Show what would be changed without modifying files"
    puts "  --type TYPE   Force a specific content type"
    puts "                Valid types: #{VALID_TYPES.join(', ')}"
    puts "  --help        Show this help message"
    puts ""
    puts "Detection priority:"
    puts "  1. Existing :_mod-docs-content-type: attribute (skip)"
    puts "  2. Legacy :_module-type: attribute (update)"
    puts "  3. Filename prefix (assembly_, con_, proc_, ref_, snip_)"
    puts "  4. Folder location (assemblies/, concepts/, procedures/, etc.)"
    puts "  5. Content patterns (.Procedure, numbered lists, tables, includes)"
    exit 0
  else
    input_file = arg
    i += 1
  end
end

if input_file.nil?
  puts "Usage: ruby content_type.rb <file.adoc> [-o output.adoc] [--dry-run] [--type TYPE]"
  puts ""
  puts "Options:"
  puts "  -o FILE       Write output to FILE (default: overwrite input)"
  puts "  --dry-run     Show what would be changed without modifying files"
  puts "  --type TYPE   Force a specific content type (#{VALID_TYPES.join(', ')})"
  exit 1
end

unless File.exist?(input_file)
  puts "Error: File not found: #{input_file}"
  exit 1
end

result = process_file(input_file, forced_type)

unless result[:modified]
  puts "#{input_file}: #{result[:reason]}"
  exit 0
end

if dry_run
  case result[:action]
  when 'added'
    puts "#{input_file}: Would add :_mod-docs-content-type: #{result[:type]} at line #{result[:line]}"
  when 'updated'
    puts "#{input_file}: Would update #{result[:old_attr]} to :_mod-docs-content-type: #{result[:type]}"
  end
  exit 0
end

output_file ||= input_file

tmp = Tempfile.new(['adoc', '.adoc'], File.dirname(output_file))
tmp.write(result[:lines].join("\n") + "\n")
tmp.close
FileUtils.mv(tmp.path, output_file)

case result[:action]
when 'added'
  puts "#{output_file}: Added :_mod-docs-content-type: #{result[:type]}"
when 'updated'
  puts "#{output_file}: Updated #{result[:old_attr]} to :_mod-docs-content-type: #{result[:type]}"
end
