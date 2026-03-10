#!/usr/bin/env ruby
# frozen_string_literal: true
# entity_reference.rb
# Replaces unsupported HTML character entity references with Unicode equivalents.
# Usage: ruby entity_reference.rb <file.adoc> [-o output.adoc]

require 'tempfile'
require 'fileutils'

# Mapping of HTML entities to Unicode characters
# Excludes &amp;, &lt;, &gt;, &apos;, &quot; which are supported in DITA
ENTITY_MAP = {
  # Spaces and breaks
  "&nbsp;" => "\u00A0",
  "&ensp;" => "\u2002",
  "&emsp;" => "\u2003",
  "&thinsp;" => "\u2009",

  # Dashes and hyphens
  "&ndash;" => "\u2013",
  "&mdash;" => "\u2014",
  "&minus;" => "\u2212",
  "&hyphen;" => "\u2010",

  # Quotation marks
  "&lsquo;" => "\u2018",
  "&rsquo;" => "\u2019",
  "&sbquo;" => "\u201A",
  "&ldquo;" => "\u201C",
  "&rdquo;" => "\u201D",
  "&bdquo;" => "\u201E",
  "&laquo;" => "\u00AB",
  "&raquo;" => "\u00BB",
  "&lsaquo;" => "\u2039",
  "&rsaquo;" => "\u203A",

  # Punctuation
  "&hellip;" => "\u2026",
  "&middot;" => "\u00B7",
  "&bull;" => "\u2022",
  "&prime;" => "\u2032",
  "&Prime;" => "\u2033",
  "&dagger;" => "\u2020",
  "&Dagger;" => "\u2021",
  "&sect;" => "\u00A7",
  "&para;" => "\u00B6",

  # Currency
  "&cent;" => "\u00A2",
  "&pound;" => "\u00A3",
  "&yen;" => "\u00A5",
  "&euro;" => "\u20AC",
  "&curren;" => "\u00A4",

  # Math and symbols
  "&times;" => "\u00D7",
  "&divide;" => "\u00F7",
  "&plusmn;" => "\u00B1",
  "&frac12;" => "\u00BD",
  "&frac14;" => "\u00BC",
  "&frac34;" => "\u00BE",
  "&deg;" => "\u00B0",
  "&sup1;" => "\u00B9",
  "&sup2;" => "\u00B2",
  "&sup3;" => "\u00B3",
  "&micro;" => "\u00B5",
  "&permil;" => "\u2030",
  "&infin;" => "\u221E",
  "&asymp;" => "\u2248",
  "&ne;" => "\u2260",
  "&le;" => "\u2264",
  "&ge;" => "\u2265",
  "&sum;" => "\u2211",
  "&prod;" => "\u220F",
  "&radic;" => "\u221A",
  "&part;" => "\u2202",
  "&nabla;" => "\u2207",
  "&int;" => "\u222B",
  "&isin;" => "\u2208",
  "&notin;" => "\u2209",
  "&empty;" => "\u2205",
  "&forall;" => "\u2200",
  "&exist;" => "\u2203",
  "&and;" => "\u2227",
  "&or;" => "\u2228",
  "&not;" => "\u00AC",

  # Arrows
  "&larr;" => "\u2190",
  "&rarr;" => "\u2192",
  "&uarr;" => "\u2191",
  "&darr;" => "\u2193",
  "&harr;" => "\u2194",
  "&lArr;" => "\u21D0",
  "&rArr;" => "\u21D2",
  "&uArr;" => "\u21D1",
  "&dArr;" => "\u21D3",
  "&hArr;" => "\u21D4",

  # Special characters
  "&copy;" => "\u00A9",
  "&reg;" => "\u00AE",
  "&trade;" => "\u2122",
  "&loz;" => "\u25CA",
  "&spades;" => "\u2660",
  "&clubs;" => "\u2663",
  "&hearts;" => "\u2665",
  "&diams;" => "\u2666",

  # Greek letters (common ones)
  "&alpha;" => "\u03B1",
  "&beta;" => "\u03B2",
  "&gamma;" => "\u03B3",
  "&delta;" => "\u03B4",
  "&epsilon;" => "\u03B5",
  "&zeta;" => "\u03B6",
  "&eta;" => "\u03B7",
  "&theta;" => "\u03B8",
  "&iota;" => "\u03B9",
  "&kappa;" => "\u03BA",
  "&lambda;" => "\u03BB",
  "&mu;" => "\u03BC",
  "&nu;" => "\u03BD",
  "&xi;" => "\u03BE",
  "&omicron;" => "\u03BF",
  "&pi;" => "\u03C0",
  "&rho;" => "\u03C1",
  "&sigma;" => "\u03C3",
  "&tau;" => "\u03C4",
  "&upsilon;" => "\u03C5",
  "&phi;" => "\u03C6",
  "&chi;" => "\u03C7",
  "&psi;" => "\u03C8",
  "&omega;" => "\u03C9",
  "&Alpha;" => "\u0391",
  "&Beta;" => "\u0392",
  "&Gamma;" => "\u0393",
  "&Delta;" => "\u0394",
  "&Epsilon;" => "\u0395",
  "&Zeta;" => "\u0396",
  "&Eta;" => "\u0397",
  "&Theta;" => "\u0398",
  "&Iota;" => "\u0399",
  "&Kappa;" => "\u039A",
  "&Lambda;" => "\u039B",
  "&Mu;" => "\u039C",
  "&Nu;" => "\u039D",
  "&Xi;" => "\u039E",
  "&Omicron;" => "\u039F",
  "&Pi;" => "\u03A0",
  "&Rho;" => "\u03A1",
  "&Sigma;" => "\u03A3",
  "&Tau;" => "\u03A4",
  "&Upsilon;" => "\u03A5",
  "&Phi;" => "\u03A6",
  "&Chi;" => "\u03A7",
  "&Psi;" => "\u03A8",
  "&Omega;" => "\u03A9",

  # Accented characters
  "&Agrave;" => "\u00C0",
  "&Aacute;" => "\u00C1",
  "&Acirc;" => "\u00C2",
  "&Atilde;" => "\u00C3",
  "&Auml;" => "\u00C4",
  "&Aring;" => "\u00C5",
  "&AElig;" => "\u00C6",
  "&Ccedil;" => "\u00C7",
  "&Egrave;" => "\u00C8",
  "&Eacute;" => "\u00C9",
  "&Ecirc;" => "\u00CA",
  "&Euml;" => "\u00CB",
  "&Igrave;" => "\u00CC",
  "&Iacute;" => "\u00CD",
  "&Icirc;" => "\u00CE",
  "&Iuml;" => "\u00CF",
  "&ETH;" => "\u00D0",
  "&Ntilde;" => "\u00D1",
  "&Ograve;" => "\u00D2",
  "&Oacute;" => "\u00D3",
  "&Ocirc;" => "\u00D4",
  "&Otilde;" => "\u00D5",
  "&Ouml;" => "\u00D6",
  "&Oslash;" => "\u00D8",
  "&Ugrave;" => "\u00D9",
  "&Uacute;" => "\u00DA",
  "&Ucirc;" => "\u00DB",
  "&Uuml;" => "\u00DC",
  "&Yacute;" => "\u00DD",
  "&THORN;" => "\u00DE",
  "&szlig;" => "\u00DF",
  "&agrave;" => "\u00E0",
  "&aacute;" => "\u00E1",
  "&acirc;" => "\u00E2",
  "&atilde;" => "\u00E3",
  "&auml;" => "\u00E4",
  "&aring;" => "\u00E5",
  "&aelig;" => "\u00E6",
  "&ccedil;" => "\u00E7",
  "&egrave;" => "\u00E8",
  "&eacute;" => "\u00E9",
  "&ecirc;" => "\u00EA",
  "&euml;" => "\u00EB",
  "&igrave;" => "\u00EC",
  "&iacute;" => "\u00ED",
  "&icirc;" => "\u00EE",
  "&iuml;" => "\u00EF",
  "&eth;" => "\u00F0",
  "&ntilde;" => "\u00F1",
  "&ograve;" => "\u00F2",
  "&oacute;" => "\u00F3",
  "&ocirc;" => "\u00F4",
  "&otilde;" => "\u00F5",
  "&ouml;" => "\u00F6",
  "&oslash;" => "\u00F8",
  "&ugrave;" => "\u00F9",
  "&uacute;" => "\u00FA",
  "&ucirc;" => "\u00FB",
  "&uuml;" => "\u00FC",
  "&yacute;" => "\u00FD",
  "&thorn;" => "\u00FE",
  "&yuml;" => "\u00FF"
}.freeze

# Entities that are supported in DITA and should NOT be replaced
SUPPORTED_ENTITIES = %w[&amp; &lt; &gt; &apos; &quot;].freeze

def process_file(path)
  content = File.read(path, encoding: "UTF-8")
  lines = content.lines.map(&:chomp)

  in_comment_block = false
  comment_delimiter = nil
  in_code_block = false
  code_delimiter = nil
  replacements_enabled = false
  replacement_count = 0
  unknown_entities = []

  processed_lines = lines.map.with_index do |line, idx|
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
      next line
    end
    next line if in_comment_block

    # Skip single-line comments
    next line if line =~ %r{^//($|[^/])}

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
        replacements_enabled = false
      end
      next line
    end

    # Check for subs attribute enabling replacements in code blocks
    if line =~ /^\[.*subs=['"](?:[^'"]*,\s*)?\+?(?:replacements|normal).*['"]\s*\]/
      replacements_enabled = true unless line =~ /-replacements/
      next line
    end

    # Skip processing inside code blocks unless replacements is enabled
    if in_code_block && !replacements_enabled
      next line
    end

    # Reset replacements flag outside code blocks
    replacements_enabled = false unless in_code_block

    # Find and replace entity references
    processed_line = line.gsub(/&[a-zA-Z][a-zA-Z0-9]*;/) do |entity|
      # Skip supported entities
      if SUPPORTED_ENTITIES.include?(entity)
        entity
      elsif ENTITY_MAP.key?(entity)
        replacement_count += 1
        ENTITY_MAP[entity]
      else
        # Track unknown entities for reporting
        unless unknown_entities.any? { |e| e[:entity] == entity }
          unknown_entities << { line: idx + 1, entity: entity }
        end
        entity
      end
    end

    processed_line
  end

  { lines: processed_lines, count: replacement_count, unknown: unknown_entities }
end

# Parse command line arguments
input_file = nil
output_file = nil
dry_run = false

i = 0
while i < ARGV.length
  arg = ARGV[i]
  case arg
  when "-o"
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
  when "--dry-run", "-n"
    dry_run = true
    i += 1
  when "--help", "-h"
    puts "Usage: ruby entity_reference.rb <file.adoc> [-o output.adoc] [--dry-run]"
    puts ""
    puts "Options:"
    puts "  -o FILE     Write output to FILE (default: overwrite input)"
    puts "  --dry-run   Show what would be changed without modifying files"
    exit 0
  else
    input_file = arg
    i += 1
  end
end

if input_file.nil?
  puts "Usage: ruby entity_reference.rb <file.adoc> [-o output.adoc] [--dry-run]"
  puts ""
  puts "Options:"
  puts "  -o FILE     Write output to FILE (default: overwrite input)"
  puts "  --dry-run   Show what would be changed without modifying files"
  exit 1
end

unless File.exist?(input_file)
  puts "Error: File not found: #{input_file}"
  exit 1
end

result = process_file(input_file)

if result[:count].zero? && result[:unknown].empty?
  puts "#{input_file}: No entity references to replace"
  exit 0
end

if dry_run
  puts "#{input_file}: Would replace #{result[:count]} entity reference(s)"
  unless result[:unknown].empty?
    puts "  Unknown entities (not replaced):"
    result[:unknown].each do |u|
      puts "    Line #{u[:line]}: #{u[:entity]}"
    end
  end
  exit 0
end

output_file ||= input_file

tmp = Tempfile.new(["adoc", ".adoc"], File.dirname(output_file))
tmp.write(result[:lines].join("\n") + "\n")
tmp.close
FileUtils.mv(tmp.path, output_file)

puts "#{output_file}: Replaced #{result[:count]} entity reference(s)"
unless result[:unknown].empty?
  puts "  Unknown entities (not replaced):"
  result[:unknown].each do |u|
    puts "    Line #{u[:line]}: #{u[:entity]}"
  end
end
