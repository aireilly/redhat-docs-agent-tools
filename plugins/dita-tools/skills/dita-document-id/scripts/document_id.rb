#!/usr/bin/env ruby
# document_id.rb
# Adds missing document IDs for AsciiDoc files.
# Usage: ruby document_id.rb <file.adoc> [-o output.adoc]

require 'tempfile'
require 'fileutils'

# Generate an AsciiDoc-style ID from filename
def generate_id_from_filename(filename, use_context: true)
  id = File.basename(filename, '.adoc')

  # Add {context} suffix if requested
  id = "#{id}_{context}" if use_context

  id
end

def process_file(path, use_context: true)
  content = File.read(path)
  lines = content.lines.map(&:chomp)

  # Detect if this is an assembly file - assemblies don't use {context} suffix
  is_assembly = content.include?(':_mod-docs-content-type: ASSEMBLY')
  use_context = false if is_assembly

  in_comment_block = false
  comment_delimiter = nil
  in_code_block = false
  code_delimiter = nil
  assigned_id = false
  id_added = false
  title_line_idx = nil

  # First pass: find if there's already an ID
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
      next
    end
    next if in_code_block

    # Check for ID attribute (various formats)
    # [id="some-id"]
    # [[some-id]]
    # [#some-id]
    if line =~ /^\[(?:id=['"]?|#|\[)[A-Za-z_:{}][A-Za-z0-9_.:{}-]*(?:['"]?,?[^\]]*|\][^\]]*|,[^\]]*\]?|['"]?\]?)\]\s*$/
      assigned_id = true
      next
    end

    # Skip other attribute lists
    next if line =~ /^\[(?:|[\w.#%{,"'].*)\]\s*$/

    # Skip attribute definitions
    next if line =~ /^:!?\S[^:]*:/

    # Skip empty lines
    next if line =~ /^\s*$/

    # Skip conditionals (unless they contain the title)
    if line =~ /^(?:ifn?def|ifeval|endif)::\S*\[.*\]\s*$/
      # Check if this is a conditional containing a title
      if line =~ /^ifn?def::\S*\[=\s+[^\]]+\]\s*$/
        title_line_idx = idx
        break
      end
      next
    end

    # Check for document title (level 0 heading)
    if line =~ /^=\s+\S.*$/
      title_line_idx = idx
      break
    end

    # Any other content resets the ID tracking
    assigned_id = false
  end

  # If no title found or ID already assigned, nothing to do
  if title_line_idx.nil?
    return { lines: lines, modified: false, reason: 'No document title found' }
  end

  if assigned_id
    return { lines: lines, modified: false, reason: 'ID already assigned' }
  end

  # Skip adding IDs to master.adoc files - they typically don't need document IDs
  if File.basename(path) == 'master.adoc'
    return { lines: lines, modified: false, reason: 'Skipping master.adoc (no ID added to assembly index files)' }
  end

  # Extract title text
  title_line = lines[title_line_idx]
  title_text = if title_line =~ /^ifn?def::\S*\[=\s+([^\]]+)\]\s*$/
                 Regexp.last_match(1).strip
               elsif title_line =~ /^=\s+(.+)$/
                 Regexp.last_match(1).strip
               else
                 return { lines: lines, modified: false, reason: 'Could not parse title' }
               end

  # Generate ID from filename
  generated_id = generate_id_from_filename(path, use_context: use_context)

  # Insert ID line before title
  id_line = "[id=\"#{generated_id}\"]"
  lines.insert(title_line_idx, id_line)

  { lines: lines, modified: true, id: generated_id, title: title_text }
end

# Parse command line arguments
input_file = nil
output_file = nil
dry_run = false
no_context = false

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
  when '--no-context'
    no_context = true
    i += 1
  when '--help', '-h'
    puts "Usage: ruby document_id.rb <file.adoc> [-o output.adoc] [--dry-run] [--no-context]"
    puts ""
    puts "Options:"
    puts "  -o FILE       Write output to FILE (default: overwrite input)"
    puts "  --dry-run     Show what would be changed without modifying files"
    puts "  --no-context  Generate ID without _{context} suffix"
    exit 0
  else
    input_file = arg
    i += 1
  end
end

if input_file.nil?
  puts "Usage: ruby document_id.rb <file.adoc> [-o output.adoc] [--dry-run] [--no-context]"
  puts ""
  puts "Options:"
  puts "  -o FILE       Write output to FILE (default: overwrite input)"
  puts "  --dry-run     Show what would be changed without modifying files"
  puts "  --no-context  Generate ID without _{context} suffix"
  exit 1
end

unless File.exist?(input_file)
  puts "Error: File not found: #{input_file}"
  exit 1
end

result = process_file(input_file, use_context: !no_context)

unless result[:modified]
  puts "#{input_file}: #{result[:reason]}"
  exit 0
end

if dry_run
  puts "#{input_file}: Would add ID [id=\"#{result[:id]}\"]"
  puts "  Title: #{result[:title]}"
  exit 0
end

output_file ||= input_file

tmp = Tempfile.new(['adoc', '.adoc'], File.dirname(output_file))
tmp.write(result[:lines].join("\n") + "\n")
tmp.close
FileUtils.mv(tmp.path, output_file)

puts "#{output_file}: Added ID [id=\"#{result[:id]}\"]"
puts "  Title: #{result[:title]}"
