#!/usr/bin/env ruby
# callouts.rb
# Usage: ruby callouts.rb <file.adoc> [--rewrite-bullets | --rewrite-deflists | --add-inline-comments] [-o output.adoc] [--dry-run]
#
# Options:
#   --rewrite-bullets      Convert callouts to bullet lists after the code block (default)
#   --rewrite-deflists     Convert callouts to definition lists after the code block
#   --add-inline-comments  Convert callouts to inline comments in the code block
#   --dry-run              Show what would be changed without modifying files
#   -o <file>              Write output to specified file instead of modifying in place

require 'asciidoctor'
require 'tempfile'
require 'fileutils'
require 'set'

# Supported source block languages for callout transformation
SUPPORTED_LANGUAGES = /^(yaml|yml|bash|sh|shell|console|terminal|cmd)$/i

# Find all conditional attributes used in the file (ifdef::attr[] and ifndef::attr[])
# Handles both block form (ifdef::attr[]) and inline form (ifdef::attr[content])
# Returns a Set of attribute names
def find_conditional_attributes(content)
  attrs = Set.new
  # Match both ifdef::attr[] and ifdef::attr[content] forms
  content.scan(/(?:ifdef|ifndef)::(\S+)\[/) do |match|
    attrs.add(match[0])
  end
  attrs
end

# Find source blocks by parsing with Asciidoctor using given attributes
# Returns array of hashes with :code_start, :code_end (0-indexed line numbers)
# Parses multiple times with different attribute combinations to find blocks inside conditionals
def find_source_blocks_with_conditionals(content, lines)
  blocks = []
  seen_ranges = Set.new

  # Find all conditional attributes
  attrs = find_conditional_attributes(content)

  # Generate attribute combinations to try
  # For each attribute, we try with it set (for ifdef) and without (for ifndef)
  combinations = [{}]  # Start with no attributes set
  attrs.each do |attr|
    combinations << { attr => '' }  # Set the attribute (value doesn't matter, just needs to be defined)
  end

  combinations.each do |attr_hash|
    doc = Asciidoctor.load(content, sourcemap: true, attributes: attr_hash)

    doc.find_by(context: :listing) do |block|
      next unless block.style == 'source'
      next unless block.lines

      # Check if language matches supported types
      lang = block.attr('language')
      next unless lang =~ SUPPORTED_LANGUAGES

      # Check if there are any callouts in the block's content
      has_callouts = block.lines.any? { |l| l =~ /<\d+>/ }
      next unless has_callouts

      # Find this block in the original file by matching content
      # Look for a line with callout marker that matches
      callout_line = block.lines.find { |l| l =~ /<\d+>/ }
      next unless callout_line

      # Search original lines for this callout line
      code_start = nil
      code_end = nil
      lines.each_with_index do |line, idx|
        if line.strip == callout_line.strip
          # Found a matching line, now find the enclosing ---- block
          # Search backwards for opening ----
          opening = idx - 1
          opening -= 1 while opening >= 0 && lines[opening] !~ /^----\s*$/
          next if opening < 0

          # Search forwards for closing ----
          closing = idx + 1
          closing += 1 while closing < lines.length && lines[closing] !~ /^----\s*$/
          next if closing >= lines.length

          # Verify all block.lines match the content in this range
          candidate_start = opening + 1
          candidate_end = closing
          candidate_lines = lines[candidate_start...candidate_end].map(&:strip)
          block_content = block.lines.map(&:strip)

          if candidate_lines == block_content
            code_start = candidate_start
            code_end = candidate_end
            break
          end
        end
      end
      next unless code_start && code_end

      # Use code_start..code_end as unique identifier to avoid duplicates
      range_key = "#{code_start}-#{code_end}"
      next if seen_ranges.include?(range_key)
      seen_ranges.add(range_key)

      # Find the [source,...] line before the opening ----
      block_line = code_start - 2  # -1 for ----, -1 for [source,...]
      block_line -= 1 while block_line >= 0 && lines[block_line] !~ /^\[source,/i

      blocks << { code_start: code_start, code_end: code_end, block_line: block_line }
    end
  end

  # Sort by code_start to process in order
  blocks.sort_by { |b| b[:code_start] }
end

# Process file with inline comments mode (original behavior)
# Converts callout markers to inline comments within the code block
def process_file_inline_comments(path)
  content = File.read(path)
  lines = content.lines.map(&:chomp)
  modifications = []

  # Find all source blocks, including those inside conditionals
  source_blocks = find_source_blocks_with_conditionals(content, lines)

  source_blocks.each do |block_info|
    code_start = block_info[:code_start]
    code_end = block_info[:code_end]
    block_line = block_info[:block_line]
    callout_start = code_end + 1

    # Skip any endif/ifdef/ifndef conditionals after the code block
    # This handles cases where the code block is wrapped in ifdef::[]
    #   ----
    #   endif::[]
    #   +
    #   <1> Callout definition
    while callout_start < lines.length &&
          (lines[callout_start] =~ /^(ifdef|ifndef)::\S+\[\]/ || lines[callout_start] =~ /^endif::\[\]/)
      callout_start += 1
    end

    # Skip any + continuation marker after the code block (and conditionals)
    # This handles cases like:
    #   ----
    #   +
    #   <1> Callout definition
    has_continuation = false
    if callout_start < lines.length && lines[callout_start] =~ /^\+\s*$/
      has_continuation = true
      callout_start += 1
    end

    # Check if callout region contains ifdef/ifndef conditionals
    # Inline comments mode cannot handle conditional callouts - use --rewrite-deflists instead
    has_conditionals = false
    scan_idx = callout_start
    while scan_idx < lines.length
      scan_line = lines[scan_idx]
      if scan_line =~ /^(ifdef|ifndef)::\S+\[\]/
        has_conditionals = true
        break
      end
      # Stop scanning at blank line or non-callout/non-conditional line
      break if scan_line =~ /^\s*$/ && scan_line !~ /^<\d+>/ && scan_line !~ /^endif::\[\]/
      break unless scan_line =~ /^<\d+>/ || scan_line =~ /^(ifdef|ifndef|endif)::/
      scan_idx += 1
    end
    if has_conditionals
      STDERR.puts "Warning: Skipping code block at line #{block_line + 1} - callouts contain ifdef/ifndef conditionals. Use --rewrite-deflists mode instead."
      next
    end

    # Extract callout definitions from source (including multi-line)
    callout_map = {}
    callout_line_counts = {}
    j = callout_start
    while j < lines.length
      line = lines[j]

      # Skip conditional directives (ifdef::attr[], ifndef::attr[], endif::[])
      if line =~ /^(ifdef|ifndef)::\S+\[\]/ || line =~ /^endif::\[\]/
        j += 1
        next
      end

      # Exit if we hit a blank line or non-callout line
      break unless line =~ /^<(\d+)>\s*(.*)$/

      num = $1.to_i
      text_lines = [$2.strip]
      j += 1
      # Capture continuation lines (not starting with <N>, not blank, not conditionals)
      while j < lines.length &&
            lines[j] !~ /^<\d+>/ &&
            lines[j] !~ /^\s*$/ &&
            lines[j] !~ /^(ifdef|ifndef)::\S+\[\]/ &&
            lines[j] !~ /^endif::\[\]/
        text_lines << lines[j].strip
        j += 1
      end
      # Use first definition for each callout number
      unless callout_map[num]
        callout_map[num] = text_lines.join(' ')
        callout_line_counts[num] = text_lines.length
      end
    end

    # Process code lines
    new_code = []
    (code_start...code_end).each do |line_idx|
      line = lines[line_idx]

      if line =~ /^(\s*)(.*?)\s*<(\d+)>\s*$/
        indent = $1
        content = $2.rstrip
        num = $3.to_i

        # Skip transformation if callout definition is more than 3 lines
        if callout_line_counts[num] && callout_line_counts[num] > 3
          new_code << line
          next
        end

        # Remove trailing # if callout was preceded by comment marker (e.g., "# <1>")
        if content =~ /^(.*?)\s*#\s*$/
          content = $1.rstrip
        end

        if callout_map[num]
          new_code << "#{indent}# #{callout_map[num]}"
        end
        new_code << "#{indent}#{content}" unless content.empty?
      else
        new_code << line
      end
    end

    # Find end of callout definitions and preserve those with > 3 lines
    # Also handles ifdef/ifndef/endif blocks around callouts
    callout_end = callout_start
    preserved_callouts = []
    while callout_end < lines.length
      line = lines[callout_end]

      # Skip conditional directives (ifdef::attr[], ifndef::attr[], endif::[])
      if line =~ /^(ifdef|ifndef)::\S+\[\]/ || line =~ /^endif::\[\]/
        callout_end += 1
        next
      end

      # Exit if we hit a blank line or non-callout line
      break unless line =~ /^<(\d+)>/

      num = $1.to_i
      callout_def_start = callout_end
      callout_end += 1
      # Skip continuation lines (not callouts, not blank, not conditionals)
      while callout_end < lines.length &&
            lines[callout_end] !~ /^<\d+>/ &&
            lines[callout_end] !~ /^\s*$/ &&
            lines[callout_end] !~ /^(ifdef|ifndef)::\S+\[\]/ &&
            lines[callout_end] !~ /^endif::\[\]/
        callout_end += 1
      end
      # Preserve callout definitions that were skipped (> 3 lines)
      if callout_line_counts[num] && callout_line_counts[num] > 3
        preserved_callouts.concat(lines[callout_def_start...callout_end])
      end
    end

    modifications << {
      start: code_start,
      end: callout_end,
      replacement: new_code + [lines[code_end]] + preserved_callouts
    }
  end

  # Apply modifications in reverse order
  modifications.reverse.each do |mod|
    lines[mod[:start]...mod[:end]] = mod[:replacement]
  end

  lines
end

# Process file with definition list mode
# Converts callouts to definition lists after the code block
# Removes callout markers from code and creates a "Where:" definition list
# The definition term is the cleaned code line content
def process_file_deflists(path)
  content = File.read(path)
  lines = content.lines.map(&:chomp)
  modifications = []

  # Find all source blocks, including those inside conditionals
  source_blocks = find_source_blocks_with_conditionals(content, lines)

  source_blocks.each do |block_info|
    code_start = block_info[:code_start]
    code_end = block_info[:code_end]
    block_line = block_info[:block_line]
    callout_start = code_end + 1

    # Skip any endif/ifdef/ifndef conditionals after the code block
    # This handles cases where the code block is wrapped in ifdef::[]
    #   ----
    #   endif::[]
    #   +
    #   <1> Callout definition
    while callout_start < lines.length &&
          (lines[callout_start] =~ /^(ifdef|ifndef)::\S+\[\]/ || lines[callout_start] =~ /^endif::\[\]/)
      callout_start += 1
    end

    # Skip any + continuation marker after the code block (and conditionals)
    # This handles cases like:
    #   ----
    #   +
    #   <1> Callout definition
    has_continuation = false
    if callout_start < lines.length && lines[callout_start] =~ /^\+\s*$/
      has_continuation = true
      callout_start += 1
    end

    # Extract the code line content for each callout to use as definition term
    # Map callout number -> cleaned code line content
    # This is done first so we can use it when transforming callout lines
    code_line_map = {}
    (code_start...code_end).each do |line_idx|
      line = lines[line_idx]
      if line =~ /^(\s*)(.*?)\s*<(\d+)>\s*$/
        code_content = $2.rstrip
        num = $3.to_i

        # Remove trailing # if callout was preceded by comment marker (e.g., "# <1>")
        if code_content =~ /^(.*?)\s*#\s*$/
          code_content = $1.rstrip
        end

        # Remove trailing \ for line continuations
        code_content = code_content.sub(/\s*\\$/, '').rstrip

        code_line_map[num] = code_content unless code_content.empty?
      end
    end

    # Process code lines - remove all callout markers
    new_code = []
    (code_start...code_end).each do |line_idx|
      line = lines[line_idx]

      if line =~ /^(\s*)(.*?)\s*<(\d+)>\s*$/
        indent = $1
        code_content = $2.rstrip

        # Remove trailing # if callout was preceded by comment marker (e.g., "# <1>")
        if code_content =~ /^(.*?)\s*#\s*$/
          code_content = $1.rstrip
        end

        new_code << "#{indent}#{code_content}" unless code_content.empty?
      else
        new_code << line
      end
    end

    # Find end of callout definitions
    # Also handles ifdef/ifndef/endif blocks around callouts
    callout_end = callout_start
    while callout_end < lines.length
      line = lines[callout_end]

      # Skip conditional directives (ifdef::attr[], ifndef::attr[], endif::[])
      if line =~ /^(ifdef|ifndef)::\S+\[\]/ || line =~ /^endif::\[\]/
        callout_end += 1
        next
      end

      # Exit if we hit a blank line or non-callout line
      break unless line =~ /^<\d+>/

      callout_end += 1
      # Skip continuation lines (not callouts, not blank, not conditionals)
      while callout_end < lines.length &&
            lines[callout_end] !~ /^<\d+>/ &&
            lines[callout_end] !~ /^\s*$/ &&
            lines[callout_end] !~ /^(ifdef|ifndef)::\S+\[\]/ &&
            lines[callout_end] !~ /^endif::\[\]/
        callout_end += 1
      end
    end

    # Skip any trailing + continuation marker after callout definitions
    # This removes the original list attachment marker since we're replacing the callouts
    if callout_end < lines.length && lines[callout_end] =~ /^\+\s*$/
      callout_end += 1
    end

    # Build definition list wrapped in an open block attached to code block
    # Uses + continuation and -- open block delimiters per AsciiDoc spec
    # Preserves ifdef/ifndef/endif structure around conditional callouts
    deflist_lines = []
    deflist_lines << "+"
    deflist_lines << "--"

    # Iterate through the callout region and transform each line
    j = callout_start
    while j < callout_end
      line = lines[j]

      # Preserve conditional directives as-is
      if line =~ /^(ifdef|ifndef)::\S+\[\]/ || line =~ /^endif::\[\]/
        deflist_lines << line
        j += 1
        next
      end

      # Transform callout lines to definition list entries
      if line =~ /^<(\d+)>\s*(.*)$/
        num = $1.to_i
        text_lines = [$2.strip]
        j += 1

        # Capture continuation lines (not starting with <N>, not blank, not conditionals)
        while j < callout_end &&
              lines[j] !~ /^<\d+>/ &&
              lines[j] !~ /^\s*$/ &&
              lines[j] !~ /^(ifdef|ifndef)::\S+\[\]/ &&
              lines[j] !~ /^endif::\[\]/
          text_lines << lines[j].strip
          j += 1
        end

        callout_text = text_lines.join(' ')

        # Use the code line content as the definition term
        term = if code_line_map[num]
                 code_line_map[num]
               else
                 "Line #{num}"
               end

        deflist_lines << "`#{term}`:: #{callout_text}"
      else
        # Skip any other lines (shouldn't happen, but be safe)
        j += 1
      end
    end

    deflist_lines << "--"

    modifications << {
      start: code_start,
      end: callout_end,
      replacement: new_code + [lines[code_end]] + deflist_lines
    }
  end

  # Apply modifications in reverse order
  modifications.reverse.each do |mod|
    lines[mod[:start]...mod[:end]] = mod[:replacement]
  end

  lines
end

# Process file with bullet list mode
# Converts callouts to bullet lists after the code block
# Removes callout markers from code and creates a bulleted list
# Each bullet uses the cleaned code line content in backticks followed by the callout description
# Follows the Red Hat supplementary style guide "Bulleted lists" format
def process_file_bullets(path)
  content = File.read(path)
  lines = content.lines.map(&:chomp)
  modifications = []

  # Find all source blocks, including those inside conditionals
  source_blocks = find_source_blocks_with_conditionals(content, lines)

  source_blocks.each do |block_info|
    code_start = block_info[:code_start]
    code_end = block_info[:code_end]
    block_line = block_info[:block_line]
    callout_start = code_end + 1

    # Skip any endif/ifdef/ifndef conditionals after the code block
    while callout_start < lines.length &&
          (lines[callout_start] =~ /^(ifdef|ifndef)::\S+\[\]/ || lines[callout_start] =~ /^endif::\[\]/)
      callout_start += 1
    end

    # Skip any + continuation marker after the code block (and conditionals)
    has_continuation = false
    if callout_start < lines.length && lines[callout_start] =~ /^\+\s*$/
      has_continuation = true
      callout_start += 1
    end

    # Extract the code line content for each callout to use in bullet text
    code_line_map = {}
    (code_start...code_end).each do |line_idx|
      line = lines[line_idx]
      if line =~ /^(\s*)(.*?)\s*<(\d+)>\s*$/
        code_content = $2.rstrip
        num = $3.to_i

        # Remove trailing # if callout was preceded by comment marker (e.g., "# <1>")
        if code_content =~ /^(.*?)\s*#\s*$/
          code_content = $1.rstrip
        end

        # Remove trailing \ for line continuations
        code_content = code_content.sub(/\s*\\$/, '').rstrip

        code_line_map[num] = code_content unless code_content.empty?
      end
    end

    # Process code lines - remove all callout markers
    new_code = []
    (code_start...code_end).each do |line_idx|
      line = lines[line_idx]

      if line =~ /^(\s*)(.*?)\s*<(\d+)>\s*$/
        indent = $1
        code_content = $2.rstrip

        # Remove trailing # if callout was preceded by comment marker (e.g., "# <1>")
        if code_content =~ /^(.*?)\s*#\s*$/
          code_content = $1.rstrip
        end

        new_code << "#{indent}#{code_content}" unless code_content.empty?
      else
        new_code << line
      end
    end

    # Find end of callout definitions
    callout_end = callout_start
    while callout_end < lines.length
      line = lines[callout_end]

      # Skip conditional directives (ifdef::attr[], ifndef::attr[], endif::[])
      if line =~ /^(ifdef|ifndef)::\S+\[\]/ || line =~ /^endif::\[\]/
        callout_end += 1
        next
      end

      # Exit if we hit a blank line or non-callout line
      break unless line =~ /^<\d+>/

      callout_end += 1
      # Skip continuation lines (not callouts, not blank, not conditionals)
      while callout_end < lines.length &&
            lines[callout_end] !~ /^<\d+>/ &&
            lines[callout_end] !~ /^\s*$/ &&
            lines[callout_end] !~ /^(ifdef|ifndef)::\S+\[\]/ &&
            lines[callout_end] !~ /^endif::\[\]/
        callout_end += 1
      end
    end

    # Skip any trailing + continuation marker after callout definitions
    if callout_end < lines.length && lines[callout_end] =~ /^\+\s*$/
      callout_end += 1
    end

    # Build bullet list wrapped in an open block attached to code block
    bullet_lines = []
    bullet_lines << "+"
    bullet_lines << "--"

    # Iterate through the callout region and transform each line
    j = callout_start
    while j < callout_end
      line = lines[j]

      # Preserve conditional directives as-is
      if line =~ /^(ifdef|ifndef)::\S+\[\]/ || line =~ /^endif::\[\]/
        bullet_lines << line
        j += 1
        next
      end

      # Transform callout lines to bullet list entries
      if line =~ /^<(\d+)>\s*(.*)$/
        num = $1.to_i
        text_lines = [$2.strip]
        j += 1

        # Capture continuation lines (not starting with <N>, not blank, not conditionals)
        while j < callout_end &&
              lines[j] !~ /^<\d+>/ &&
              lines[j] !~ /^\s*$/ &&
              lines[j] !~ /^(ifdef|ifndef)::\S+\[\]/ &&
              lines[j] !~ /^endif::\[\]/
          text_lines << lines[j].strip
          j += 1
        end

        callout_text = text_lines.join(' ')

        # Use the code line content as the bullet term
        term = if code_line_map[num]
                 code_line_map[num]
               else
                 "Line #{num}"
               end

        bullet_lines << "* `#{term}` #{callout_text}"
      else
        # Skip any other lines
        j += 1
      end
    end

    bullet_lines << "--"

    modifications << {
      start: code_start,
      end: callout_end,
      replacement: new_code + [lines[code_end]] + bullet_lines
    }
  end

  # Apply modifications in reverse order
  modifications.reverse.each do |mod|
    lines[mod[:start]...mod[:end]] = mod[:replacement]
  end

  lines
end

# Parse command line arguments
input_file = nil
output_file = nil
mode = :bullets  # default mode
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
      i += 1
    end
  when /^-o(.+)$/
    output_file = $1
    i += 1
  when '--rewrite-bullets'
    mode = :bullets
    i += 1
  when '--add-inline-comments'
    mode = :inline_comments
    i += 1
  when '--rewrite-deflists'
    mode = :deflists
    i += 1
  when '--dry-run'
    dry_run = true
    i += 1
  else
    input_file = arg
    i += 1
  end
end

if input_file.nil?
  puts "Usage: ruby callouts.rb <file.adoc> [--rewrite-bullets | --rewrite-deflists | --add-inline-comments] [-o output.adoc] [--dry-run]"
  puts ""
  puts "Options:"
  puts "  --rewrite-bullets      Convert callouts to bullet lists after the code block (default)"
  puts "  --rewrite-deflists     Convert callouts to definition lists after the code block"
  puts "  --add-inline-comments  Convert callouts to inline comments in the code block"
  puts "  --dry-run              Show what would be changed without modifying files"
  puts "  -o <file>              Write output to specified file instead of modifying in place"
  exit 1
end

unless File.exist?(input_file)
  puts "Error: File not found: #{input_file}"
  exit 1
end

output_file ||= input_file

# Process based on mode
output = case mode
         when :bullets
           process_file_bullets(input_file)
         when :deflists
           process_file_deflists(input_file)
         else
           process_file_inline_comments(input_file)
         end

if dry_run
  puts "=== DRY RUN: Would write to #{output_file} ==="
  puts output.join("\n")
else
  tmp = Tempfile.new(['adoc', '.adoc'], File.dirname(output_file))
  tmp.write(output.join("\n") + "\n")
  tmp.close
  FileUtils.mv(tmp.path, output_file)
  mode_name = case mode
              when :bullets then 'bullet lists'
              when :deflists then 'definition lists'
              else 'inline comments'
              end
  puts "Wrote to #{output_file} (mode: #{mode_name})"
end
