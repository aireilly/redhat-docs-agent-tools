#!/usr/bin/env ruby
# frozen_string_literal: true

# search_tech_references.rb
# Searches cloned code repositories for evidence matching extracted technical references.
# Takes refs JSON (output of extract_tech_references.rb) + repo paths as input.
# Returns raw search evidence JSON. Does NOT assign confidence or suggest fixes.
# Usage: ruby search_tech_references.rb <refs.json> <repo_path> [<repo_path>...] [--output results.json] [--verbose] [--dry-run]

require 'json'
require 'fileutils'
require 'open3'

class TechReferenceSearcher
  DEFINITION_PATTERNS = {
    function: [
      /\bdef\s+%<name>s\b/,
      /\bfunc\s+%<name>s\b/,
      /\bfunction\s+%<name>s\b/,
      /\b%<name>s\s*=\s*(?:function|=>|\()/,
      /\b(?:async\s+)?(?:def|fn)\s+%<name>s\b/
    ],
    class: [
      /\bclass\s+%<name>s\b/,
      /\binterface\s+%<name>s\b/,
      /\bstruct\s+%<name>s\b/,
      /\btype\s+%<name>s\b/,
      /\benum\s+%<name>s\b/
    ]
  }.freeze

  CONFIG_EXTENSIONS = %w[.yaml .yml .json .toml .conf .cfg .ini .properties].freeze

  # Skip binary and generated directories during grep
  SKIP_DIRS = %w[.git node_modules vendor __pycache__ .tox .eggs dist build].freeze

  def initialize(verbose: false)
    @verbose = verbose
    @results = []
    @counters = { total: 0, found: 0, not_found: 0 }
  end

  def search(refs_data, repo_paths)
    references = refs_data['references'] || refs_data[:references] || {}

    search_commands(references['commands'] || references[:commands] || [], repo_paths)
    search_code_blocks(references['code_blocks'] || references[:code_blocks] || [], repo_paths)
    search_apis(references['apis'] || references[:apis] || [], repo_paths)
    search_configs(references['configs'] || references[:configs] || [], repo_paths)
    search_file_paths(references['file_paths'] || references[:file_paths] || [], repo_paths)

    {
      search_results: @results,
      summary: @counters
    }
  end

  private

  # ---------------------------------------------------------------------------
  # Commands
  # ---------------------------------------------------------------------------
  def search_commands(commands, repo_paths)
    commands.each_with_index do |cmd, idx|
      @counters[:total] += 1
      ref_id = "cmd-#{idx + 1}"
      raw_command = cmd['command'] || cmd[:command] || ''
      debug "Searching for command: #{raw_command}"

      # Parse command name and flags
      parts = raw_command.split(/\s+/)
      binary = parts.first&.gsub(/^(sudo\s+)/, '')
      flags = parts.select { |p| p.start_with?('-') }

      matches = []
      git_evidence = []
      flags_checked = {}

      repo_paths.each do |repo|
        next unless File.directory?(repo)

        # Find binary by name in repo
        binary_matches = find_files_by_name(repo, binary)
        binary_matches.each do |path|
          matches << { repo: repo, path: path, type: 'binary', context: "Binary found: #{path}" }
        end

        # Grep for command name in code/scripts
        grep_hits = grep_repo(repo, binary, max_results: 10)
        grep_hits.each do |hit|
          matches << { repo: repo, path: hit[:path], type: 'grep', context: hit[:context] }
        end

        # Git log for rename/removal evidence
        log_entries = git_log_search(repo, binary, max_results: 5)
        log_entries.each do |entry|
          git_evidence << { repo: repo, type: 'log', context: entry }
        end

        # Check each flag exists in the repo
        flags.each do |flag|
          next if flag.length < 2

          flag_hits = grep_repo(repo, Regexp.escape(flag), max_results: 3)
          flags_checked[flag] = !flag_hits.empty?
          debug "  Flag #{flag}: #{flags_checked[flag] ? 'found' : 'not found'}"
        end
      end

      found = !matches.empty?
      @counters[found ? :found : :not_found] += 1

      @results << {
        ref_id: ref_id,
        category: 'command',
        reference: cmd,
        results: {
          found: found,
          matches: matches,
          git_evidence: git_evidence,
          flags_checked: flags_checked
        }
      }
    end
  end

  # ---------------------------------------------------------------------------
  # Code blocks
  # ---------------------------------------------------------------------------
  def search_code_blocks(blocks, repo_paths)
    blocks.each_with_index do |block, idx|
      @counters[:total] += 1
      ref_id = "code-#{idx + 1}"
      content = block['content'] || block[:content] || ''
      language = block['language'] || block[:language] || 'text'
      debug "Searching for code block (#{language}): #{content[0..60]}..."

      matches = []
      lines = content.lines.map(&:chomp).reject(&:empty?)
      next if lines.empty?

      first_line = lines.first.strip
      # Extract key identifiers from the block
      identifiers = extract_identifiers(content)

      repo_paths.each do |repo|
        next unless File.directory?(repo)

        # Grep for exact first-line match
        unless first_line.empty?
          first_line_hits = grep_repo(repo, Regexp.escape(first_line), max_results: 5)
          first_line_hits.each do |hit|
            matches << { repo: repo, path: hit[:path], type: 'first_line', context: hit[:context] }
          end
        end

        # Check identifier match ratio
        if identifiers.any?
          found_ids = []
          missing_ids = []
          identifiers.each do |ident|
            hits = grep_repo(repo, "\\b#{Regexp.escape(ident)}\\b", max_results: 1)
            if hits.any?
              found_ids << ident
            else
              missing_ids << ident
            end
          end

          total_ids = identifiers.length
          found_count = found_ids.length
          ratio = total_ids.positive? ? (found_count.to_f / total_ids).round(2) : 0.0

          matches << {
            repo: repo,
            path: nil,
            type: 'identifier_ratio',
            context: "#{found_count}/#{total_ids} identifiers found (#{ratio})",
            found_identifiers: found_ids,
            missing_identifiers: missing_ids
          }
        end
      end

      found = matches.any? { |m| m[:type] != 'identifier_ratio' || m[:context].include?('/') }
      @counters[found ? :found : :not_found] += 1

      @results << {
        ref_id: ref_id,
        category: 'code_block',
        reference: block,
        results: {
          found: found,
          matches: matches,
          git_evidence: []
        }
      }
    end
  end

  # ---------------------------------------------------------------------------
  # APIs (functions, classes, endpoints)
  # ---------------------------------------------------------------------------
  def search_apis(apis, repo_paths)
    apis.each_with_index do |api, idx|
      @counters[:total] += 1
      ref_id = "api-#{idx + 1}"
      api_type = api['type'] || api[:type] || 'function'
      name = api['name'] || api[:name] || ''
      debug "Searching for #{api_type}: #{name}"

      matches = []
      git_evidence = []

      next if name.empty? || name.length < 2

      repo_paths.each do |repo|
        next unless File.directory?(repo)

        case api_type
        when 'function'
          # Grep for definition patterns
          DEFINITION_PATTERNS[:function].each do |pattern_template|
            pattern = format(pattern_template.source, name: Regexp.escape(name))
            hits = grep_repo(repo, pattern, max_results: 5)
            hits.each do |hit|
              matches << {
                repo: repo,
                path: hit[:path],
                type: 'definition',
                context: hit[:context]
              }
            end
          end

          # Also grep for general usage
          usage_hits = grep_repo(repo, "\\b#{Regexp.escape(name)}\\b", max_results: 5)
          usage_hits.each do |hit|
            matches << { repo: repo, path: hit[:path], type: 'usage', context: hit[:context] }
          end

        when 'class'
          DEFINITION_PATTERNS[:class].each do |pattern_template|
            pattern = format(pattern_template.source, name: Regexp.escape(name))
            hits = grep_repo(repo, pattern, max_results: 5)
            hits.each do |hit|
              matches << {
                repo: repo,
                path: hit[:path],
                type: 'definition',
                context: hit[:context]
              }
            end
          end

        when 'endpoint'
          # Grep for endpoint path in route definitions and code
          endpoint_hits = grep_repo(repo, Regexp.escape(name), max_results: 10)
          endpoint_hits.each do |hit|
            matches << { repo: repo, path: hit[:path], type: 'endpoint', context: hit[:context] }
          end
        end

        # Git log for rename/deprecation evidence
        log_entries = git_log_search(repo, name, max_results: 3)
        log_entries.each do |entry|
          git_evidence << { repo: repo, type: 'log', context: entry }
        end
      end

      found = matches.any? { |m| m[:type] == 'definition' || m[:type] == 'endpoint' }
      found = !matches.empty? unless found
      @counters[found ? :found : :not_found] += 1

      @results << {
        ref_id: ref_id,
        category: 'api',
        reference: api,
        results: {
          found: found,
          matches: matches,
          git_evidence: git_evidence
        }
      }
    end
  end

  # ---------------------------------------------------------------------------
  # Configs
  # ---------------------------------------------------------------------------
  def search_configs(configs, repo_paths)
    configs.each_with_index do |config, idx|
      @counters[:total] += 1
      ref_id = "cfg-#{idx + 1}"
      keys = config['keys'] || config[:keys] || []
      format_type = config['format'] || config[:format] || 'yaml'
      debug "Searching for config keys (#{format_type}): #{keys.join(', ')}"

      matches = []
      git_evidence = []
      keys_found = {}

      repo_paths.each do |repo|
        next unless File.directory?(repo)

        # Find config files by extension
        extensions = config_extensions_for(format_type)
        config_files = []
        extensions.each do |ext|
          config_files.concat(find_files_by_extension(repo, ext))
        end

        debug "  Found #{config_files.length} config files in #{repo}"

        # Grep for each key in config files
        keys.each do |key|
          key_found = false
          config_files.each do |cf|
            hits = grep_file(cf, key)
            next if hits.empty?

            key_found = true
            hits.each do |hit|
              matches << {
                repo: repo,
                path: cf,
                type: 'config_key',
                key: key,
                context: hit
              }
            end
          end
          keys_found[key] = key_found

          # Also search broadly if not found in config files
          unless key_found
            broad_hits = grep_repo(repo, "\\b#{Regexp.escape(key)}\\b", max_results: 3)
            broad_hits.each do |hit|
              matches << {
                repo: repo,
                path: hit[:path],
                type: 'config_key_broad',
                key: key,
                context: hit[:context]
              }
              keys_found[key] = true
            end
          end
        end

        # Git log for deprecation/rename evidence on missing keys
        keys.each do |key|
          next if keys_found[key]

          log_entries = git_log_search(repo, key, max_results: 3)
          log_entries.each do |entry|
            git_evidence << { repo: repo, key: key, type: 'log', context: entry }
          end
        end
      end

      found = keys_found.values.any?
      @counters[found ? :found : :not_found] += 1

      @results << {
        ref_id: ref_id,
        category: 'config',
        reference: config,
        results: {
          found: found,
          matches: matches,
          git_evidence: git_evidence,
          keys_checked: keys_found
        }
      }
    end
  end

  # ---------------------------------------------------------------------------
  # File paths
  # ---------------------------------------------------------------------------
  def search_file_paths(paths, repo_paths)
    paths.each_with_index do |fp, idx|
      @counters[:total] += 1
      ref_id = "path-#{idx + 1}"
      path = fp['path'] || fp[:path] || ''
      debug "Searching for file path: #{path}"

      matches = []

      next if path.empty?

      repo_paths.each do |repo|
        next unless File.directory?(repo)

        # Check exact path existence
        exact = File.join(repo, path)
        if File.exist?(exact)
          matches << {
            repo: repo,
            path: path,
            type: 'exact',
            context: "Exact path exists: #{path}"
          }
          debug "  Exact match found: #{exact}"
          next
        end

        # Find by basename if not at exact path
        basename = File.basename(path)
        basename_matches = find_files_by_name(repo, basename)
        basename_matches.each do |found_path|
          matches << {
            repo: repo,
            path: found_path,
            type: 'basename',
            context: "Found by basename at: #{found_path}"
          }
        end
      end

      found = !matches.empty?
      @counters[found ? :found : :not_found] += 1

      @results << {
        ref_id: ref_id,
        category: 'file_path',
        reference: fp,
        results: {
          found: found,
          matches: matches,
          git_evidence: []
        }
      }
    end
  end

  # ---------------------------------------------------------------------------
  # Helper methods
  # ---------------------------------------------------------------------------

  # Grep a repository for a pattern using system grep
  def grep_repo(repo, pattern, max_results: 10)
    exclude_args = SKIP_DIRS.map { |d| "--exclude-dir=#{d}" }.join(' ')
    cmd = "grep -rn #{exclude_args} --include='*' -E #{shell_escape(pattern)} #{shell_escape(repo)} 2>/dev/null"
    output = run_command(cmd, timeout: 15)
    return [] if output.nil? || output.empty?

    results = []
    output.lines.each do |line|
      line = line.chomp
      next if line.empty?

      # Parse grep output: filepath:linenum:content
      if (m = line.match(/^(.+?):(\d+):(.*)$/))
        rel_path = m[1].sub("#{repo}/", '')
        results << { path: rel_path, line: m[2].to_i, context: m[3].strip }
      end

      break if results.length >= max_results
    end

    results
  end

  # Grep a single file for a pattern
  def grep_file(file_path, pattern)
    return [] unless File.exist?(file_path)

    cmd = "grep -n #{shell_escape(pattern)} #{shell_escape(file_path)} 2>/dev/null"
    output = run_command(cmd, timeout: 5)
    return [] if output.nil? || output.empty?

    output.lines.map(&:chomp).reject(&:empty?).first(5)
  end

  # Search git log for a term (rename/deprecation evidence)
  def git_log_search(repo, term, max_results: 5)
    return [] unless File.directory?(File.join(repo, '.git'))

    cmd = "git -C #{shell_escape(repo)} log --oneline --all -n #{max_results} " \
          "--grep=#{shell_escape(term)} 2>/dev/null"
    output = run_command(cmd, timeout: 10)
    return [] if output.nil? || output.empty?

    output.lines.map(&:chomp).reject(&:empty?).first(max_results)
  end

  # Find files by exact name in a repo
  def find_files_by_name(repo, name)
    return [] if name.nil? || name.empty?

    cmd = "find #{shell_escape(repo)} -name #{shell_escape(name)} " \
          "-not -path '*/.git/*' -not -path '*/node_modules/*' " \
          "-not -path '*/vendor/*' 2>/dev/null"
    output = run_command(cmd, timeout: 10)
    return [] if output.nil? || output.empty?

    output.lines.map { |l| l.chomp.sub("#{repo}/", '') }.reject(&:empty?).first(10)
  end

  # Find files by extension in a repo
  def find_files_by_extension(repo, ext)
    cmd = "find #{shell_escape(repo)} -name '*#{shell_escape(ext)}' " \
          "-not -path '*/.git/*' -not -path '*/node_modules/*' " \
          "-not -path '*/vendor/*' 2>/dev/null"
    output = run_command(cmd, timeout: 10)
    return [] if output.nil? || output.empty?

    output.lines.map(&:chomp).reject(&:empty?).first(50)
  end

  # Extract key identifiers from code content
  def extract_identifiers(content)
    identifiers = []

    # Function/method names
    content.scan(/\b([a-zA-Z_][a-zA-Z0-9_]{2,})\s*\(/) { |m| identifiers << m[0] }

    # Class names
    content.scan(/\b(?:class|struct|interface|type)\s+([A-Z][a-zA-Z0-9_]+)/) { |m| identifiers << m[0] }

    # Import paths / module names
    content.scan(/(?:import|from|require|use)\s+['"]?([a-zA-Z0-9_.\/\-]+)/) { |m| identifiers << m[0] }

    identifiers.uniq.first(20)
  end

  # Map config format to file extensions
  def config_extensions_for(format_type)
    case format_type.to_s.downcase
    when 'yaml', 'yml'
      %w[.yaml .yml]
    when 'json'
      %w[.json]
    when 'toml'
      %w[.toml]
    else
      CONFIG_EXTENSIONS
    end
  end

  # Shell-escape a string for safe use in commands
  def shell_escape(str)
    "'" + str.to_s.gsub("'", "'\\\\''") + "'"
  end

  # Run a shell command, return stdout or nil
  def run_command(cmd, timeout: 15)
    stdout, _stderr, status = Open3.capture3(cmd)
    return nil unless status&.success? || status&.exitstatus == 1 # grep returns 1 for no match
    stdout
  rescue Errno::ENOENT => e
    debug "Command error: #{e.message}"
    nil
  end

  def debug(message)
    warn "[DEBUG] #{message}" if @verbose
  end
end

# CLI interface
if __FILE__ == $PROGRAM_NAME
  require 'optparse'

  options = {
    output: nil,
    verbose: false,
    dry_run: false
  }

  parser = OptionParser.new do |opts|
    opts.banner = "Usage: #{$PROGRAM_NAME} <refs.json> <repo_path> [<repo_path>...] [options]"

    opts.on('-o', '--output FILE', 'Write JSON to file instead of stdout') do |file|
      options[:output] = file
    end

    opts.on('-v', '--verbose', 'Include debug output') do
      options[:verbose] = true
    end

    opts.on('--dry-run', 'Validate inputs without performing searches') do
      options[:dry_run] = true
    end

    opts.on('-h', '--help', 'Show this help') do
      puts opts
      exit 0
    end
  end

  parser.parse!

  empty_output = { search_results: [], summary: { total: 0, found: 0, not_found: 0 } }

  if ARGV.empty?
    warn "ERROR: No input files specified"
    warn parser.banner
    exit 1
  end

  refs_file = ARGV.shift
  repo_paths = ARGV

  # Handle dry-run: gracefully handle missing/invalid input
  if options[:dry_run]
    unless File.exist?(refs_file)
      json_out = JSON.pretty_generate(empty_output)
      if options[:output]
        File.write(options[:output], json_out)
        puts "Dry-run: wrote empty results to #{options[:output]}"
      else
        puts json_out
      end
      exit 0
    end

    begin
      JSON.parse(File.read(refs_file))
    rescue JSON::ParserError, Encoding::InvalidByteSequenceError
      json_out = JSON.pretty_generate(empty_output)
      if options[:output]
        File.write(options[:output], json_out)
        puts "Dry-run: wrote empty results to #{options[:output]}"
      else
        puts json_out
      end
      exit 0
    end

    json_out = JSON.pretty_generate(empty_output)
    if options[:output]
      File.write(options[:output], json_out)
      puts "Dry-run: wrote empty results to #{options[:output]}"
    else
      puts json_out
    end
    exit 0
  end

  # Normal mode: validate inputs
  unless File.exist?(refs_file)
    warn "ERROR: References file not found: #{refs_file}"
    exit 1
  end

  begin
    refs_data = JSON.parse(File.read(refs_file))
  rescue JSON::ParserError => e
    warn "ERROR: Invalid JSON in #{refs_file}: #{e.message}"
    exit 1
  end

  if repo_paths.empty?
    warn "ERROR: No repository paths specified"
    warn parser.banner
    exit 1
  end

  repo_paths.each do |rp|
    unless File.directory?(rp)
      warn "WARNING: Repository path not found: #{rp}"
    end
  end

  valid_repos = repo_paths.select { |rp| File.directory?(rp) }
  if valid_repos.empty?
    warn "ERROR: No valid repository paths found"
    exit 1
  end

  searcher = TechReferenceSearcher.new(verbose: options[:verbose])
  output = searcher.search(refs_data, valid_repos)

  json_output = JSON.pretty_generate(output)

  if options[:output]
    File.write(options[:output], json_output)
    puts "Search completed: #{options[:output]}"
    puts "  Total references: #{output[:summary][:total]}"
    puts "  Found: #{output[:summary][:found]}"
    puts "  Not found: #{output[:summary][:not_found]}"
  else
    puts json_output
  end

  exit 0
end
