#!/usr/bin/env ruby
# frozen_string_literal: true

# extract_tech_references.rb
# Extracts technical references from AsciiDoc files for validation against code repositories.
# Extracts: commands, code blocks, APIs/functions, configuration examples, file paths.
# Usage: ruby extract_tech_references.rb <file.adoc> [--output output.json] [--verbose]

require 'json'
require 'fileutils'

class TechReferenceExtractor
  SKIP_FUNCTIONS = %w[
    if for while print return len map set get new int str list dict type
    var let const def end do nil true false else case break next puts echo
    test eval
  ].freeze

  PATTERNS = {
    # Source block with language
    source_block: /^\[source(?:,\s*([a-z0-9+\-_]+))?(?:,\s*(.+))?\]\s*$/i,

    # Code fence: ```language
    code_fence_lang: /^```\s*([a-z0-9+\-_]+)?\s*$/i,
    code_delim: /^-{4,}\s*$/,
    literal_delim: /^\.{4,}\s*$/,

    # Listing block
    listing_block: /^\[listing\]\s*$/i,

    # Heading (AsciiDoc)
    heading: /^(=+)\s+(.+)$/,

    # Heading (Markdown)
    md_heading: /^(\#{1,6})\s+(.+)$/,

    # Block title
    block_title: /^\.([A-Za-z][^\n]*?)\s*$/,

    # Procedure step: . Some step
    procedure_step: /^\.\s+(.+)$/,

    # Command line: $ command --flag (outside code blocks, $ only)
    command_line: /^\$\s+(.+)$/,

    # Command line in code blocks: $ or # prompt
    command_line_code: /^[\$#]\s+(.+)$/,

    # Inline code with path: `path/to/file.ext`
    inline_code_path: /`([a-zA-Z0-9_\-.\/]+\.[a-z]{2,})`/,

    # Function call: functionName( or ClassName.method(
    function_call: /\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(/,

    # Class definition: class ClassName
    class_def: /\b(?:class|interface|struct)\s+([A-Z][a-zA-Z0-9_]*)/,

    # API endpoint: /api/v1/path
    api_endpoint: %r{(?:GET|POST|PUT|PATCH|DELETE)?\s*(/[a-z0-9/_\-{}]+)},

    # Empty line
    empty_line: /^\s*$/,

    # Comment
    comment_line: %r{^//($|[^/].*)$},
    comment_block: %r{^/{4,}\s*$}
  }.freeze

  def initialize(verbose: false)
    @verbose = verbose
    @references = {
      commands: [],
      code_blocks: [],
      apis: [],
      configs: [],
      file_paths: []
    }
  end

  def extract_from_file(file_path)
    unless File.exist?(file_path)
      warn "ERROR: File not found: #{file_path}"
      return @references
    end

    content = File.read(file_path, encoding: 'UTF-8')
    lines = content.lines.map(&:chomp)

    extract_references(file_path, lines)
  end

  def extract_from_files(file_paths)
    file_paths.each do |path|
      if File.directory?(path)
        Dir.glob(File.join(path, '**', '*.{adoc,md}')).each do |file|
          extract_from_file(file)
        end
      else
        extract_from_file(path)
      end
    end

    @references
  end

  private

  def extract_references(file_path, lines)
    in_code_block = false
    code_delimiter = nil
    current_block = nil
    current_heading = nil
    block_title = nil
    in_comment_block = false
    comment_delimiter = nil
    code_language = nil
    in_procedure_step = false
    current_step_context = nil
    skip_next_line = false

    lines.each_with_index do |line, index|
      line_num = index + 1

      # Skip delimiter line that was consumed by peek-ahead
      if skip_next_line
        skip_next_line = false
        next
      end

      # Track comment blocks
      if PATTERNS[:comment_block].match?(line)
        if in_comment_block && line == comment_delimiter
          in_comment_block = false
          comment_delimiter = nil
        else
          in_comment_block = true
          comment_delimiter = line
        end
        next
      end

      next if in_comment_block
      next if PATTERNS[:comment_line].match?(line)

      # Track headings for context (AsciiDoc and Markdown) - only outside code blocks
      if !in_code_block
        if (heading_match = PATTERNS[:heading].match(line)) || (heading_match = PATTERNS[:md_heading].match(line))
          current_heading = heading_match[2].strip
          debug "Found heading: #{current_heading}"
          next
        end
      end

      # Track block titles
      if PATTERNS[:block_title].match?(line) && !in_code_block
        block_title = line[1..-1].strip
        debug "Found block title: #{block_title}"
        next
      end

      # Detect code block start
      if !in_code_block
        language = nil
        delimiter = nil

        # [source,language]
        if (source_match = PATTERNS[:source_block].match(line))
          language = source_match[1] || 'text'
          next_line_idx = index + 1
          if next_line_idx < lines.length
            next_line = lines[next_line_idx]
            if PATTERNS[:code_delim].match?(next_line) || PATTERNS[:literal_delim].match?(next_line)
              delimiter = next_line
              skip_next_line = true
            end
          end

          in_code_block = true
          code_delimiter = delimiter
          code_language = language
          current_block = {
            file: file_path,
            line: line_num,
            language: language,
            content: [],
            context: block_title || current_heading
          }
          debug "Started source block: language=#{language}"
          next
        end

        # [listing]
        if PATTERNS[:listing_block].match?(line)
          language = 'text'
          next_line_idx = index + 1
          if next_line_idx < lines.length
            next_line = lines[next_line_idx]
            if PATTERNS[:code_delim].match?(next_line) || PATTERNS[:literal_delim].match?(next_line)
              delimiter = next_line
              skip_next_line = true
            end
          end

          in_code_block = true
          code_delimiter = delimiter
          code_language = language
          current_block = {
            file: file_path,
            line: line_num,
            language: language,
            content: [],
            context: block_title || current_heading
          }
          debug "Started listing block"
          next
        end

        # ```language
        if (fence_match = PATTERNS[:code_fence_lang].match(line))
          language = fence_match[1] || 'text'
          in_code_block = true
          code_delimiter = '```'
          code_language = language
          current_block = {
            file: file_path,
            line: line_num,
            language: language,
            content: [],
            context: block_title || current_heading
          }
          debug "Started code fence: language=#{language}"
          next
        end

        # ---- delimiter
        if PATTERNS[:code_delim].match?(line)
          language = 'text'
          in_code_block = true
          code_delimiter = line
          code_language = language
          current_block = {
            file: file_path,
            line: line_num,
            language: language,
            content: [],
            context: block_title || current_heading
          }
          debug "Started delimited code block"
          next
        end
      else
        # Inside code block
        is_end = false

        if code_delimiter == '```' && line == '```'
          is_end = true
        elsif code_delimiter && line == code_delimiter
          is_end = true
        elsif code_delimiter.nil?
          if PATTERNS[:empty_line].match?(line) ||
             PATTERNS[:source_block].match?(line) ||
             PATTERNS[:listing_block].match?(line) ||
             PATTERNS[:heading].match?(line)
            is_end = true
          end
        end

        if is_end
          # Process completed code block
          content = current_block[:content].join("\n")
          current_block[:content] = content

          # Add to code_blocks
          @references[:code_blocks] << current_block

          # Extract additional references from code content
          extract_from_code_block(current_block, file_path, current_block[:line])

          debug "Completed code block at line #{line_num}"

          # Reset state
          in_code_block = false
          code_delimiter = nil
          current_block = nil
          code_language = nil
          block_title = nil
        else
          # Accumulate content
          current_block[:content] << line
        end

        next
      end

      # Not in code block - extract inline references

      # Procedure steps
      if (step_match = PATTERNS[:procedure_step].match(line))
        in_procedure_step = true
        current_step_context = step_match[1]
        debug "Found procedure step: #{current_step_context}"
      end

      # Commands ($ command)
      if (cmd_match = PATTERNS[:command_line].match(line))
        command = cmd_match[1].strip
        @references[:commands] << {
          file: file_path,
          line: line_num,
          command: command,
          context: current_step_context || block_title || current_heading
        }
        debug "Found command: #{command}"
      end

      # Inline code paths
      line.scan(PATTERNS[:inline_code_path]) do |match|
        path = match[0]
        @references[:file_paths] << {
          file: file_path,
          line: line_num,
          path: path,
          context: current_heading
        }
        debug "Found file path: #{path}"
      end

      # API endpoints in regular text
      if (api_match = PATTERNS[:api_endpoint].match(line))
        endpoint = api_match[1]
        @references[:apis] << {
          file: file_path,
          line: line_num,
          type: 'endpoint',
          name: endpoint,
          context: current_heading
        }
        debug "Found API endpoint: #{endpoint}"
      end
    end

    # Handle unclosed block
    if in_code_block && current_block
      content = current_block[:content].join("\n")
      current_block[:content] = content
      @references[:code_blocks] << current_block
      extract_from_code_block(current_block, file_path, current_block[:line])
      warn "WARNING: Unclosed code block in #{file_path} starting at line #{current_block[:line]}"
    end

    @references
  end

  def extract_from_code_block(block, file_path, line_num)
    content = block[:content]
    language = block[:language]
    context = block[:context]

    # Extract commands from code block lines ($ and # prompts)
    content.each_line do |cline|
      if (cmd_match = PATTERNS[:command_line_code].match(cline.chomp))
        command = cmd_match[1].strip
        prompt_char = cline.chomp.lstrip[0]
        prompt_type = prompt_char == '#' ? 'root' : 'user'
        @references[:commands] << {
          file: file_path,
          line: line_num,
          command: command,
          prompt_type: prompt_type,
          context: context
        }
        debug "Found command in code block: #{command} (#{prompt_type})"
      end
    end

    # Extract function calls
    content.scan(PATTERNS[:function_call]) do |match|
      function_name = match[0]
      next if function_name.length < 3 # Skip short matches
      next if SKIP_FUNCTIONS.include?(function_name.downcase)

      @references[:apis] << {
        file: file_path,
        line: line_num,
        type: 'function',
        name: function_name,
        language: language,
        context: context
      }
      debug "Found function: #{function_name}"
    end

    # Extract class definitions
    content.scan(PATTERNS[:class_def]) do |match|
      class_name = match[0]
      @references[:apis] << {
        file: file_path,
        line: line_num,
        type: 'class',
        name: class_name,
        language: language,
        context: context
      }
      debug "Found class: #{class_name}"
    end

    # Extract config keys from YAML/JSON/TOML
    if %w[yaml yml json toml].include?(language.downcase)
      extract_config_keys(content, file_path, line_num, language, context)
    end
  end

  def extract_config_keys(content, file_path, line_num, format, context)
    keys = []

    case format.downcase
    when 'yaml', 'yml'
      # Extract YAML keys: key: value
      content.scan(/^(\s*)([a-zA-Z_][a-zA-Z0-9_-]*):/) do |indent, key|
        keys << key
      end
    when 'json'
      # Extract JSON keys: "key": value
      content.scan(/"([a-zA-Z_][a-zA-Z0-9_-]*)"\s*:/) do |key|
        keys << key[0]
      end
    when 'toml'
      # Extract TOML keys: key = value
      content.scan(/^([a-zA-Z_][a-zA-Z0-9_-]*)\s*=/) do |key|
        keys << key[0]
      end
    end

    if keys.any?
      @references[:configs] << {
        file: file_path,
        line: line_num,
        format: format,
        keys: keys.uniq,
        context: context
      }
      debug "Found config keys: #{keys.uniq.join(', ')}"
    end
  end

  def debug(message)
    puts "[DEBUG] #{message}" if @verbose
  end
end

# CLI interface
if __FILE__ == $PROGRAM_NAME
  require 'optparse'

  options = {
    output: nil,
    verbose: false
  }

  OptionParser.new do |opts|
    opts.banner = "Usage: #{$PROGRAM_NAME} <file.adoc> [options]"

    opts.on('-o', '--output FILE', 'Write JSON to file instead of stdout') do |file|
      options[:output] = file
    end

    opts.on('-v', '--verbose', 'Include debug output') do
      options[:verbose] = true
    end

    opts.on('-h', '--help', 'Show this help') do
      puts opts
      exit 0
    end
  end.parse!

  if ARGV.empty?
    warn "ERROR: No input files specified"
    warn "Usage: #{$PROGRAM_NAME} <file.adoc> [options]"
    exit 1
  end

  extractor = TechReferenceExtractor.new(verbose: options[:verbose])
  references = extractor.extract_from_files(ARGV)

  # Add summary
  output = {
    summary: {
      commands: references[:commands].length,
      code_blocks: references[:code_blocks].length,
      apis: references[:apis].length,
      configs: references[:configs].length,
      file_paths: references[:file_paths].length
    },
    references: references
  }

  json_output = JSON.pretty_generate(output)

  if options[:output]
    File.write(options[:output], json_output)
    puts "Extracted technical references to #{options[:output]}"
    puts "  Commands: #{references[:commands].length}"
    puts "  Code blocks: #{references[:code_blocks].length}"
    puts "  APIs: #{references[:apis].length}"
    puts "  Configs: #{references[:configs].length}"
    puts "  File paths: #{references[:file_paths].length}"
  else
    puts json_output
  end

  exit 0
end
