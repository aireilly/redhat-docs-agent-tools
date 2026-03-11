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
  # Well-known external commands NOT expected to live in the code repo.
  # Commands matching this list are tagged scope=external so the LLM can skip them.
  EXTERNAL_COMMANDS = %w[
    sudo su dnf yum rpm apt dpkg pip pip3 npm yarn gem bundle cargo
    systemctl journalctl firewall-cmd nmcli ip ss curl wget scp ssh rsync
    cat head tail grep sed awk find xargs sort uniq wc tee tr cut
    cp mv rm mkdir chmod chown ln tar gzip gunzip zip unzip
    git svn docker podman buildah skopeo
    oc kubectl helm kustomize
    ansible ansible-playbook ansible-galaxy
    make cmake gcc g++ javac python python3 ruby node go rustc
    cd ls echo printf export source test set unset read
    openssl keytool certbot
    mount umount fdisk parted lsblk blkid
    useradd usermod groupadd passwd chpasswd
    crontab at
    vi vim nano emacs
    man info help
    less more pg
    ps kill top htop
    nc nmap tcpdump
    date cal uptime hostname uname whoami id
    env printenv
    true false exit
    subscription-manager yum-config-manager dnf5
    virsh virt-install qemu-img qemu-system-x86_64
    ssh-keygen ssh-copy-id ssh-add
    jq yq xmllint
    base64 sha256sum md5sum
    diff patch
    systemd-analyze loginctl timedatectl localectl hostnamectl
  ].freeze

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
    @schemas = {}
    @cli_definitions = {}
    @binary_name_cache = {}
  end

  def search(refs_data, repo_paths)
    references = refs_data['references'] || refs_data[:references] || {}

    # Pre-discovery: find schemas and CLI definitions for deterministic validation
    @schemas = discover_schemas(repo_paths)
    @cli_definitions = discover_cli_definitions(repo_paths)

    debug "Discovered #{@schemas.length} schema files"
    debug "Discovered #{@cli_definitions.length} CLI entry points"

    search_commands(references['commands'] || references[:commands] || [], repo_paths)
    search_code_blocks(references['code_blocks'] || references[:code_blocks] || [], repo_paths)
    search_apis(references['apis'] || references[:apis] || [], repo_paths)
    search_configs(references['configs'] || references[:configs] || [], repo_paths)
    search_file_paths(references['file_paths'] || references[:file_paths] || [], repo_paths)

    {
      search_results: @results,
      summary: @counters,
      discovered_schemas: @schemas.keys,
      discovered_cli_definitions: @cli_definitions.map { |k, v| { binary: k, file: v[:file], subcommands: v[:subcommands].keys } }
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
      parts = shell_split_simple(raw_command)
      # Strip leading sudo
      parts.shift if parts.first == 'sudo'
      binary = parts.first || ''
      flags = parts.select { |p| p.start_with?('-') }

      # Classify scope
      scope = classify_command_scope(binary, repo_paths)
      debug "  Scope: #{scope}"

      matches = []
      git_evidence = []
      flags_checked = {}
      cli_validation = nil

      # Skip expensive repo searches for external commands — the triage will
      # discard them anyway. Still record the result so it appears in the output.
      unless scope == 'external'
        escaped_binary = Regexp.escape(binary)

        repo_paths.each do |repo|
          next unless File.directory?(repo)

          # Find binary by name in repo
          binary_matches = find_files_by_name(repo, binary)
          binary_matches.each do |path|
            matches << { repo: repo, path: path, type: 'binary', context: "Binary found: #{path}" }
          end

          # Grep for command name in code/scripts
          grep_hits = grep_repo(repo, "\\b#{escaped_binary}\\b", max_results: 10)
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

        # Validate against discovered CLI definitions (argparse/click/etc.)
        if @cli_definitions.key?(binary)
          cli_validation = validate_command_against_cli(binary, parts[1..] || [], @cli_definitions[binary])
          debug "  CLI validation: #{cli_validation[:valid] ? 'valid' : 'issues found'}"
        end
      end

      found = !matches.empty?
      @counters[found ? :found : :not_found] += 1

      @results << {
        ref_id: ref_id,
        category: 'command',
        scope: scope,
        reference: cmd,
        results: {
          found: found,
          matches: matches,
          git_evidence: git_evidence,
          flags_checked: flags_checked,
          cli_validation: cli_validation
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

      # Validate config keys against discovered schemas
      schema_validation = nil
      unless @schemas.empty?
        schema_validation = validate_config_against_schemas(keys, @schemas)
        debug "  Schema validation: #{schema_validation[:matched_schemas].length} schemas checked"
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
          keys_checked: keys_found,
          schema_validation: schema_validation
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
  # Scope classification
  # ---------------------------------------------------------------------------

  # Classify whether a command binary is in-scope (lives in the code repo),
  # external (common system/tool command), or unknown.
  # This is a lightweight check — it does NOT do full repo searches (those happen
  # in search_commands). It only checks the EXTERNAL_COMMANDS list and project
  # entry point metadata to avoid duplicating the work search_commands already does.
  def classify_command_scope(binary, repo_paths)
    return 'external' if binary.nil? || binary.empty?
    return 'external' if EXTERNAL_COMMANDS.include?(binary)

    # Check if binary is declared as an entry point in project metadata.
    # This is cheap (reads a few small files) and avoids the broad grep fallback.
    repo_paths.each do |repo|
      next unless File.directory?(repo)

      %w[pyproject.toml setup.cfg setup.py Cargo.toml package.json].each do |ep_file|
        ep_path = File.join(repo, ep_file)
        next unless File.exist?(ep_path)

        hits = grep_file(ep_path, binary)
        return 'in-scope' unless hits.empty?
      end
    end

    # Don't fall back to broad grep — that's too noisy for short names.
    # search_commands will do the full search and the LLM can use those
    # results alongside scope=unknown to make a judgment.
    'unknown'
  end

  # ---------------------------------------------------------------------------
  # Schema discovery and validation
  # ---------------------------------------------------------------------------

  # Discover schema files (JSON Schema, YAML schema, etc.) in code repos.
  # Returns a hash of { file_path => { repo:, keys:, content: } }
  def discover_schemas(repo_paths)
    schemas = {}

    repo_paths.each do |repo|
      next unless File.directory?(repo)

      # Find schema files by naming convention
      schema_patterns = %w[
        *schema*.yaml *schema*.yml *schema*.json
        *_schema.* *.schema.* *-schema.*
      ]

      schema_files = []
      schema_patterns.each do |pattern|
        cmd = "find #{shell_escape(repo)} -iname #{shell_escape(pattern)} " \
              "-not -path '*/.git/*' -not -path '*/node_modules/*' " \
              "-not -path '*/vendor/*' -not -path '*/__pycache__/*' 2>/dev/null"
        output = run_command(cmd, timeout: 10)
        next if output.nil? || output.empty?

        schema_files.concat(output.lines.map(&:chomp).reject(&:empty?))
      end

      schema_files.uniq.each do |sf|
        begin
          content = File.read(sf, encoding: 'UTF-8')
          keys = extract_all_keys_from_content(content, sf)
          rel_path = sf.sub("#{repo}/", '')
          schemas[rel_path] = { repo: repo, full_path: sf, keys: keys }
          debug "  Found schema: #{rel_path} (#{keys.length} keys)"
        rescue StandardError => e
          debug "  Error reading schema #{sf}: #{e.message}"
        end
      end
    end

    schemas
  end

  # Extract all key names from a YAML/JSON file (flat list, no hierarchy).
  def extract_all_keys_from_content(content, file_path)
    keys = []

    ext = File.extname(file_path).downcase
    case ext
    when '.yaml', '.yml'
      content.scan(/^\s*([a-zA-Z_][a-zA-Z0-9_-]*)\s*:/) { |m| keys << m[0] }
    when '.json'
      content.scan(/"([a-zA-Z_][a-zA-Z0-9_-]*)"\s*:/) { |m| keys << m[0] }
    end

    keys.uniq
  end

  # Validate documented config keys against discovered schemas.
  # Returns which schemas matched and which keys are missing/extra.
  def validate_config_against_schemas(doc_keys, schemas)
    matched_schemas = []

    schemas.each do |schema_path, schema_info|
      schema_keys = schema_info[:keys]
      next if schema_keys.empty?

      # Calculate overlap
      common = doc_keys & schema_keys
      doc_only = doc_keys - schema_keys
      schema_only = schema_keys - doc_keys
      overlap_ratio = doc_keys.empty? ? 0.0 : (common.length.to_f / doc_keys.length).round(2)

      # Only report schemas with meaningful overlap (>= 30% of doc keys match)
      next if overlap_ratio < 0.3

      matched_schemas << {
        schema_file: schema_path,
        overlap_ratio: overlap_ratio,
        keys_in_both: common,
        keys_only_in_doc: doc_only,
        keys_only_in_schema: schema_only
      }
    end

    { matched_schemas: matched_schemas.sort_by { |s| -s[:overlap_ratio] } }
  end

  # ---------------------------------------------------------------------------
  # CLI definition discovery (argparse, click, etc.)
  # ---------------------------------------------------------------------------

  # Discover CLI argument definitions from Python argparse/click, Go cobra, etc.
  # Returns a hash of { binary_name => { file:, subcommands:, flags: } }
  def discover_cli_definitions(repo_paths)
    cli_defs = {}

    repo_paths.each do |repo|
      next unless File.directory?(repo)

      # Cache the binary name for this repo (same answer regardless of source file)
      binary_name = determine_binary_name_cached(repo)
      next if binary_name.nil?

      # Find Python files with argparse or click — deduplicate by file path
      argparse_hits = grep_repo(repo, 'argparse|add_argument|click\\.command|click\\.option|click\\.argument', max_results: 30)
      argparse_file_paths = argparse_hits.map { |h| h[:path] }.uniq

      argparse_file_paths.each do |rel_path|
        file_path = File.join(repo, rel_path)
        next unless File.exist?(file_path)

        begin
          content = File.read(file_path, encoding: 'UTF-8')
          defs = extract_cli_from_python(content, rel_path)
          next if defs.nil?

          if cli_defs.key?(binary_name)
            cli_defs[binary_name][:subcommands].merge!(defs[:subcommands])
            cli_defs[binary_name][:flags].concat(defs[:flags]).uniq!
          else
            cli_defs[binary_name] = defs.merge(file: rel_path)
          end

          debug "  Found CLI defs for '#{binary_name}' in #{rel_path}: #{defs[:flags].length} flags, #{defs[:subcommands].length} subcommands"
        rescue StandardError => e
          debug "  Error parsing CLI defs from #{rel_path}: #{e.message}"
        end
      end

      # Find Go files with cobra commands — deduplicate by file path
      cobra_hits = grep_repo(repo, 'cobra\\.Command|pflag|flag\\.String|flag\\.Bool', max_results: 20)
      cobra_file_paths = cobra_hits.map { |h| h[:path] }.uniq

      cobra_file_paths.each do |rel_path|
        file_path = File.join(repo, rel_path)
        next unless File.exist?(file_path)

        begin
          content = File.read(file_path, encoding: 'UTF-8')
          defs = extract_cli_from_go_cobra(content, rel_path)
          next if defs.nil?

          if cli_defs.key?(binary_name)
            cli_defs[binary_name][:subcommands].merge!(defs[:subcommands])
            cli_defs[binary_name][:flags].concat(defs[:flags]).uniq!
          else
            cli_defs[binary_name] = defs.merge(file: rel_path)
          end
        rescue StandardError => e
          debug "  Error parsing Cobra defs from #{rel_path}: #{e.message}"
        end
      end
    end

    cli_defs
  end

  # Extract flags and subcommands from Python argparse/click code
  def extract_cli_from_python(content, file_path)
    flags = []
    subcommands = {}

    # argparse: parser.add_argument('--flag', '-f', ...)
    content.scan(/add_argument\(\s*['"](-{1,2}[a-zA-Z0-9_-]+)['"]/m) do |m|
      flags << m[0]
    end
    # Also capture short flags in multi-arg add_argument calls
    content.scan(/add_argument\(\s*['"](-[a-zA-Z])['"],\s*['"](-{2}[a-zA-Z0-9_-]+)['"]/m) do |short, long|
      flags << short unless flags.include?(short)
      flags << long unless flags.include?(long)
    end

    # argparse subparsers: add_parser('subcommand')
    content.scan(/add_parser\(\s*['"]([a-zA-Z0-9_-]+)['"]/m) do |m|
      subcommands[m[0]] = { source: file_path }
    end

    # click: @click.option('--flag')
    content.scan(/@click\.option\(\s*['"](-{1,2}[a-zA-Z0-9_-]+)['"]/m) do |m|
      flags << m[0]
    end

    # click: @click.argument('name')
    content.scan(/@click\.argument\(\s*['"]([a-zA-Z0-9_-]+)['"]/m) do |m|
      subcommands[m[0]] = { source: file_path, type: 'argument' }
    end

    # click: @click.command() / @click.group()
    content.scan(/@(?:click\.command|click\.group)\(\s*(?:name\s*=\s*)?['"]([a-zA-Z0-9_-]+)['"]/m) do |m|
      subcommands[m[0]] = { source: file_path }
    end

    return nil if flags.empty? && subcommands.empty?

    { flags: flags.uniq, subcommands: subcommands }
  end

  # Extract flags and subcommands from Go cobra command definitions
  def extract_cli_from_go_cobra(content, file_path)
    flags = []
    subcommands = {}

    # cobra: cmd.Flags().StringVar(&x, "flag-name", ...)
    content.scan(/\.(?:Flags|PersistentFlags)\(\)\.(?:String|Bool|Int|Float|Duration|StringSlice)(?:Var|VarP|P)?\(\s*(?:&\w+,\s*)?["']([a-zA-Z0-9_-]+)["']/m) do |m|
      flags << "--#{m[0]}"
    end

    # cobra: Use: "subcommand"
    content.scan(/Use:\s*["']([a-zA-Z0-9_-]+)/m) do |m|
      subcommands[m[0]] = { source: file_path }
    end

    return nil if flags.empty? && subcommands.empty?

    { flags: flags.uniq, subcommands: subcommands }
  end

  # Cached wrapper — binary name depends on the repo, not the source file
  def determine_binary_name_cached(repo)
    return @binary_name_cache[repo] if @binary_name_cache.key?(repo)

    @binary_name_cache[repo] = determine_binary_name(repo)
  end

  # Determine the binary name from project metadata or repo directory name
  def determine_binary_name(repo)
    # Check pyproject.toml for [project.scripts] or [tool.poetry.scripts]
    pyproject_path = File.join(repo, 'pyproject.toml')
    if File.exist?(pyproject_path)
      begin
        content = File.read(pyproject_path, encoding: 'UTF-8')
        # Extract entries from [project.scripts] or [tool.poetry.scripts] sections
        in_scripts_section = false
        content.each_line do |line|
          stripped = line.strip
          # Detect start of a scripts section
          if stripped.match?(/^\[(?:project\.scripts|tool\.poetry\.scripts)\]/)
            in_scripts_section = true
            next
          end
          # Any other section header ends the scripts section
          if stripped.match?(/^\[/) && in_scripts_section
            in_scripts_section = false
            next
          end
          # Inside scripts section: binary-name = "module:func"
          if in_scripts_section
            if (m = stripped.match(/^["']?([a-zA-Z0-9_-]+)["']?\s*=\s*["']/))
              return m[1]
            end
          end
        end
      rescue StandardError
        # fall through
      end
    end

    # Check setup.cfg for [options.entry_points] console_scripts
    setup_cfg_path = File.join(repo, 'setup.cfg')
    if File.exist?(setup_cfg_path)
      begin
        content = File.read(setup_cfg_path, encoding: 'UTF-8')
        in_entry_points = false
        in_console_scripts = false
        content.each_line do |line|
          stripped = line.strip
          if stripped == '[options.entry_points]'
            in_entry_points = true
            next
          end
          if stripped.match?(/^\[/) && in_entry_points
            in_entry_points = false
            in_console_scripts = false
            next
          end
          if in_entry_points && stripped == 'console_scripts ='
            in_console_scripts = true
            next
          end
          if in_console_scripts && (m = stripped.match(/^([a-zA-Z0-9_-]+)\s*=/))
            return m[1]
          end
        end
      rescue StandardError
        # fall through
      end
    end

    # Check setup.py for entry_points console_scripts
    setup_py_path = File.join(repo, 'setup.py')
    if File.exist?(setup_py_path)
      begin
        content = File.read(setup_py_path, encoding: 'UTF-8')
        # console_scripts pattern: 'binary-name = module:func' or "binary-name=module:func"
        content.scan(/console_scripts.*?[\[](.*?)[\]]/m) do |block|
          block[0].scan(/['"]([a-zA-Z0-9_-]+)\s*=/) do |m|
            return m[0]
          end
        end
      rescue StandardError
        # fall through
      end
    end

    # Check Go cmd/ directory: find cmd/*/main.go patterns
    cmd_dir = File.join(repo, 'cmd')
    if File.directory?(cmd_dir)
      Dir.glob(File.join(cmd_dir, '*', 'main.go')).each do |main_go|
        # cmd/binary-name/main.go -> binary-name
        binary_dir = File.dirname(main_go)
        return File.basename(binary_dir)
      end
    end

    # Fallback: use the repo directory name
    File.basename(repo)
  end

  # Validate a documented command invocation against discovered CLI definitions.
  # Only validates flags and the first positional arg (the subcommand slot).
  # Later positionals are ordinary arguments (file paths, values) — not subcommands.
  def validate_command_against_cli(binary, args, cli_def)
    known_flags = cli_def[:flags] || []
    known_subcommands = cli_def[:subcommands] || {}

    doc_flags = args.select { |a| a.start_with?('-') }
    doc_positionals = args.reject { |a| a.start_with?('-') }

    valid_flags = []
    unknown_flags = []
    doc_flags.each do |flag|
      # Normalize: --flag=value -> --flag
      normalized = flag.split('=').first
      if known_flags.include?(normalized)
        valid_flags << normalized
      else
        unknown_flags << normalized
      end
    end

    # Only check the first positional as a potential subcommand.
    # Skip anything that looks like a file path, URL, or variable placeholder.
    subcommand_check = nil
    first_positional = doc_positionals.first
    if first_positional && !first_positional.include?('/') &&
       !first_positional.include?('.') && !first_positional.include?('<') &&
       !first_positional.match?(/^[\$\{]/) && known_subcommands.any?
      if known_subcommands.key?(first_positional)
        subcommand_check = { name: first_positional, valid: true }
      else
        subcommand_check = { name: first_positional, valid: false,
                             known_subcommands: known_subcommands.keys }
      end
    end

    {
      valid: unknown_flags.empty?,
      known_flags: known_flags,
      valid_flags: valid_flags,
      unknown_flags: unknown_flags,
      subcommand_check: subcommand_check,
      cli_source: cli_def[:file]
    }
  end

  # Simple shell-like argument splitting (handles quoted strings)
  def shell_split_simple(cmd)
    parts = []
    current = ''
    in_quote = nil

    cmd.each_char do |c|
      if in_quote
        if c == in_quote
          in_quote = nil
        else
          current << c
        end
      elsif c == '"' || c == "'"
        in_quote = c
      elsif c == ' ' || c == "\t"
        parts << current unless current.empty?
        current = ''
      else
        current << c
      end
    end
    parts << current unless current.empty?
    parts
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
