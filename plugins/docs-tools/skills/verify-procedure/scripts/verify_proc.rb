require 'open3'
require 'yaml'
require 'json'
require 'tempfile'
require 'fileutils'
require 'timeout'

# ProcedureVerifier: Validates AsciiDoc procedures as "guided exercises"
class ProcedureVerifier
  def initialize(file_path, cleanup: false)
    @file_path = file_path
    @content = File.read(file_path)
    @results = []
    @cleanup = cleanup
    @created_resources = [] # Track resources for cleanup
    @workdir = nil
    @cli_tool = detect_cli_tool
  end

  def run_verification
    puts "--- Starting Procedure Validation: #{@file_path} ---"

    # 1. Check for Best Practices (Instructional Design)
    check_best_practices

    # 2. Create a clean working directory
    @workdir = Dir.mktmpdir('verify-proc-')
    puts "[INFO] Working directory: #{@workdir}"

    begin
      # 3. Extract and Process Blocks
      blocks = extract_code_blocks

      if blocks.empty?
        puts "[ERROR] No executable steps or source blocks found."
        return
      end

      blocks.each do |block|
        process_step(block)
      end

      summarize
    ensure
      if @cleanup
        run_cleanup
      else
        puts "\n[INFO] Working directory retained at: #{@workdir}"
        puts "[INFO] Run with --cleanup to auto-delete resources and working directory after verification."
      end
    end
  end

  private

  def detect_cli_tool
    if system('which oc > /dev/null 2>&1')
      'oc'
    elsif system('which kubectl > /dev/null 2>&1')
      'kubectl'
    else
      nil
    end
  end

  # Extract AsciiDoc attribute definitions (:attr-name: value) from the document.
  # Each docs repo uses different attribute names, so we read them from the source
  # rather than hardcoding product-specific values.
  def extract_doc_attributes
    return @doc_attributes if defined?(@doc_attributes)

    @doc_attributes = {}

    # Parse :attr: value lines from the document
    @content.scan(/^:([A-Za-z0-9_-]+):\s*(.+)$/) do |name, value|
      @doc_attributes[name] = value.strip
    end

    # Also load from an optional attributes file (same dir as the .adoc, or parent)
    [File.dirname(@file_path), File.join(File.dirname(@file_path), '..')].each do |dir|
      attrs_file = File.join(dir, '_attributes.adoc')
      next unless File.exist?(attrs_file)

      File.read(attrs_file).scan(/^:([A-Za-z0-9_-]+):\s*(.+)$/) do |name, value|
        @doc_attributes[name] ||= value.strip # doc-level attrs take precedence
      end
    end

    @doc_attributes
  end

  # Resolve AsciiDoc attribute substitutions like {product-version}
  def resolve_attributes(content, has_subs)
    return content unless has_subs

    resolved = content.dup
    attrs = extract_doc_attributes

    # Replace all {attr-name} references with values found in the document
    resolved.gsub!(/\{([A-Za-z0-9_-]+)\}/) do |match|
      attr_name = $1
      if attrs.key?(attr_name)
        attrs[attr_name]
      elsif attr_name == 'product-version' && @cli_tool
        # Special case: try to detect version from a connected cluster
        detect_cluster_version || match
      else
        match # Leave unresolved attributes as-is
      end
    end

    resolved
  end

  def detect_cluster_version
    return @cluster_version if defined?(@cluster_version)

    stdout, _, status = Open3.capture3("#{@cli_tool} version -o json 2>/dev/null")
    if status.success?
      begin
        data = JSON.parse(stdout)
        # oc version returns serverVersion or openshiftVersion
        @cluster_version = data.dig('openshiftVersion')&.match(/^(\d+\.\d+)/)&.[](1)
        @cluster_version ||= data.dig('serverVersion', 'minor')&.then { |m| "1.#{m}" }
      rescue
        @cluster_version = nil
      end
    else
      @cluster_version = nil
    end

    @cluster_version
  end

  def extract_code_blocks
    blocks = []
    lines = @content.lines
    i = 0
    # Hierarchical step tracking: [major, sub, subsub]
    step_counters = [0, 0, 0]
    current_step_label = nil
    current_step_depth = 0

    ifdef_depth = 0

    while i < lines.length
      line = lines[i]

      # Track ifdef/ifndef/endif conditionals — the regex parser cannot
      # evaluate these, so warn the user that step associations may be wrong.
      if line =~ /^ifn?def::(\S+)\[/
        ifdef_depth += 1
        if ifdef_depth == 1
          puts "[WARNING] Conditional directive at line #{i + 1}: #{line.strip}"
          puts "  The parser cannot evaluate AsciiDoc conditionals. Steps inside"
          puts "  this block may be mis-numbered or associated with the wrong context."
        end
      elsif line =~ /^endif::/
        ifdef_depth -= 1 if ifdef_depth > 0
      end

      # Match numbered steps (., .., ..., etc.) to track context
      if line =~ /^(\.{1,3})\s+(.+)$/
        depth = $1.length # 1 = major, 2 = sub, 3 = subsub
        step_text = $2.strip

        # Update counters: increment at this depth, reset deeper levels
        step_counters[depth - 1] += 1
        (depth...3).each { |d| step_counters[d] = 0 }

        # Reset sub-counters when a new major step starts
        if depth == 1
          step_counters[1] = 0
          step_counters[2] = 0
        elsif depth == 2
          step_counters[2] = 0
        end

        current_step_label = format_step_label(step_counters, depth)
        current_step_depth = depth
        current_step_text = step_text
      end

      # Match source blocks with various formats:
      # [source,terminal], [source,bash], [source,yaml]
      # [source,terminal,subs="attributes+"], etc.
      if line =~ /^\[source,(terminal|bash|yaml|shell|json)(?:,(.*?))?\]\s*$/
        source_type = $1
        source_attrs = $2 || ''
        has_subs = source_attrs.include?('subs=')

        # Check if this is an example output block (preceded by "Example output" or similar)
        is_example = false
        lookback = [i - 1, 0].max
        5.times do
          break if lookback < 0
          prev_line = lines[lookback].to_s.downcase
          if prev_line.include?("example output") || prev_line.include?("output is shown") ||
             prev_line.include?("sample output") || prev_line.include?("expected output")
            is_example = true
            break
          end
          break if prev_line =~ /^\.{1,3}\s+/ # Stop at previous step
          lookback -= 1
        end

        # Find the opening ---- delimiter
        i += 1
        while i < lines.length && lines[i] !~ /^----\s*$/
          i += 1
        end

        # Extract content between ---- delimiters
        i += 1
        content_lines = []
        while i < lines.length && lines[i] !~ /^----\s*$/
          content_lines << lines[i]
          i += 1
        end

        content = content_lines.join.strip

        # Normalize terminal/shell to bash for execution
        type = %w[terminal shell].include?(source_type) ? 'bash' : source_type

        # Only add non-empty blocks
        unless content.empty?
          blocks << {
            label: current_step_label || "?",
            instruction: current_step_text || "Unknown step",
            type: type,
            content: content,
            is_example: is_example,
            has_subs: has_subs
          }
        end
      end

      i += 1
    end

    # Second pass: link YAML blocks to subsequent file-apply commands
    link_yaml_to_files(blocks)

    blocks
  end

  def format_step_label(counters, depth)
    parts = []
    parts << counters[0].to_s if counters[0] > 0
    if depth >= 2 && counters[1] > 0
      parts << ('a'..'z').to_a[counters[1] - 1]
    end
    if depth >= 3 && counters[2] > 0
      parts << ('i'..'xxvi').to_a[counters[2] - 1]
    end
    parts.join('.')
  end

  # Link source blocks to filenames mentioned in the step instruction.
  #
  # Real-world phrasing varies widely across Red Hat docs. Examples from
  # openshift-docs (via NotebookLM analysis):
  #
  #   With filename:
  #     "Create a file named load-sctp-module.yaml that contains..."
  #     "Save the following YAML manifest as integration-source-aws-ddb.yaml :"
  #     "Create a route definition called hello-openshift-route.yaml :"
  #     "Create an osc-operatorgroup.yaml manifest file:"
  #     "Create a my-pod.yaml pod manifest..."
  #     "Create a ra.yaml file that includes the following content:"
  #
  #   Without filename (should NOT match):
  #     "Apply the following YAML for a specific backing store:"
  #     "Create a config map in the Velero namespace..."
  #     "Use the following example YAML file to create the deployment:"
  #     "See the following example:"
  #
  # The instruction doesn't need to mention "YAML" — any backtick-quoted or
  # bare filename with a recognized extension is matched.
  SAVE_FILE_EXTENSIONS = /\.(?:ya?ml|json|conf|cfg|sh|txt|toml|ini|properties)/i

  def link_yaml_to_files(blocks)
    blocks.each do |block|
      next unless %w[yaml json].include?(block[:type])

      instruction = block[:instruction]

      # 1. Backtick-quoted filenames: `foo.yaml`
      if instruction =~ /`([^`]+#{SAVE_FILE_EXTENSIONS.source})`/i
        block[:save_as] = $1
      # 2. Bare filenames — must contain a path-like character pattern
      #    (word chars, hyphens, dots) ending with a recognized extension.
      #    The \b prevents matching partial words.
      elsif instruction =~ /\b([\w][\w.-]*#{SAVE_FILE_EXTENSIONS.source})\b/i
        block[:save_as] = $1
      end
    end
  end

  def check_best_practices
    # Check for a .Prerequisites section — its absence is a stronger signal
    # of "magic steps" than scanning for specific commands in the procedure body.
    # Commands like `oc login`, `sudo`, `ssh` appear in procedure steps themselves,
    # so scanning the whole file for them produces false positives.
    has_prereqs = @content.match?(/^\.Prerequisites\b/i) ||
                  @content.match?(/^\[id=.*prereq/i) ||
                  @content.match?(/^== Prerequisites/i)

    unless has_prereqs
      puts "[ADVICE] No .Prerequisites section found. Verify that prerequisites are documented or linked."
    end
  end

  def process_step(block)
    label = block[:label]
    instruction = block[:instruction]
    type = block[:type]
    content = block[:content]
    is_example = block[:is_example]
    has_subs = block[:has_subs]

    puts "\n[Step #{label}] #{instruction}"

    if is_example
      puts "[SKIP] Example output - not executed"
      return
    end

    # Resolve AsciiDoc attributes if subs="attributes+" is present
    content = resolve_attributes(content, has_subs)

    # Check for placeholders that need user input
    if has_placeholders?(content)
      puts "[SKIP] Contains placeholders requiring user input"
      puts "Content preview: #{content[0..100]}..."
      return
    end

    case type
    when 'yaml'
      validate_yaml(content, label, block[:save_as])
    when 'bash'
      execute_bash(content, label, instruction)
    when 'json'
      validate_json(content, label)
    end
  end

  def has_placeholders?(content)
    # Match angle-bracket placeholders containing underscores, spaces, or hyphens
    # (e.g., <server_hostname>, <path to file>, <api-key>)
    # but not single words that are likely legitimate values
    # (e.g., <none>, <NodePort>, <ClusterIP>, <p>, <br>)
    content.match?(/<[a-z][a-z0-9]*[_\s-][a-z0-9_\s-]+>/i) || # Multi-word placeholders
    content.match?(/\$\{[^}]+\}/) || # Variable placeholders like ${VAR}
    content.include?('CHANGEME') ||
    content.include?('REPLACE')
  end

  def validate_yaml(content, label, save_as = nil)
    begin
      # Lint the YAML for syntax errors
      YAML.safe_load(content)
      puts "[VALID] YAML syntax for Step #{label} is correct."
      @results << { step: label, status: :passed, output: "YAML syntax valid" }

      # Save the YAML to the working directory if a filename was detected
      if save_as
        dest = File.join(@workdir, save_as)
        File.write(dest, content)
        puts "[INFO] Saved YAML to #{dest}"
      end

      # If it looks like a Kubernetes resource, try dry-run validation.
      # This works with both oc and kubectl — it's a K8s API feature, not OCP-specific.
      if content.include?("apiVersion:")
        if @cli_tool
          Tempfile.open(['resource', '.yaml']) do |f|
            f.write(content)
            f.close
            stdout, stderr, status = Open3.capture3("#{@cli_tool} apply -f #{f.path} --dry-run=client")
            if status.success?
              puts "[VALID] Resource dry-run (#{@cli_tool}) passed for Step #{label}."
            else
              puts "[FAILURE] Resource validation failed: #{stderr}"
              @results.pop
              @results << { step: label, status: :failed, error: stderr.strip }
            end
          end
        else
          puts "[SKIP] No oc or kubectl found — skipping resource dry-run for Step #{label}."
        end
      end
    rescue Psych::SyntaxError => e
      puts "[FAILURE] YAML Syntax error in Step #{label}: #{e.message}"
      @results << { step: label, status: :failed, error: e.message }
    end
  end

  def validate_json(content, label)
    begin
      JSON.parse(content)
      puts "[VALID] JSON syntax for Step #{label} is correct."
      @results << { step: label, status: :passed, output: "JSON syntax valid" }
    rescue JSON::ParserError => e
      puts "[FAILURE] JSON Syntax error in Step #{label}: #{e.message}"
      @results << { step: label, status: :failed, error: e.message }
    end
  end

  def execute_bash(command, label, instruction)
    # Clean up command: remove $ prompt symbols from each line
    clean_command = command.lines.map { |line| line.sub(/^\$ /, '') }.join

    # Handle multi-line commands with backslash continuations
    if clean_command.include?('\\')
      # Join lines that end with backslash
      clean_command = clean_command.gsub(/\\\n\s*/, ' ').strip
    else
      clean_command = clean_command.strip
    end

    puts "Executing: #{clean_command[0..150]}#{clean_command.length > 150 ? '...' : ''}"

    # Run commands in the working directory with a 120-second timeout
    begin
      stdout, stderr, status = Timeout.timeout(120) do
        Open3.capture3(clean_command, chdir: @workdir)
      end
    rescue Timeout::Error
      puts "[FAILURE] Step #{label} timed out after 120 seconds."
      @results << { step: label, status: :failed, error: "Command timed out after 120 seconds" }
      puts "[WARNING] Continuing with remaining steps despite failure..."
      return
    end

    if status.success?
      puts "[SUCCESS] Step #{label} executed."

      # Track created resources for cleanup
      track_resource(clean_command, stdout)

      # Show output if it's a verification/check command
      if instruction.downcase.match?(/verify|check|confirm|retrieve|identify/)
        puts "Output: #{stdout.strip[0..200]}" unless stdout.strip.empty?
        puts "-> Verification successfully performed."
      end

      @results << { step: label, status: :passed, output: stdout.strip }
    else
      puts "[FAILURE] Step #{label} failed."
      puts "STDERR: #{stderr.strip}" unless stderr.strip.empty?
      puts "STDOUT: #{stdout.strip}" unless stdout.strip.empty?
      @results << { step: label, status: :failed, error: stderr.strip }

      # Don't exit immediately - continue with warnings
      puts "[WARNING] Continuing with remaining steps despite failure..."
    end
  end

  # Track resources created by oc/kubectl create/apply for cleanup
  def track_resource(command, stdout)
    # Match "oc create -f file.yaml" or "oc apply -f file.yaml"
    if command =~ /\b(oc|kubectl)\s+(create|apply)\s+-f\s+(\S+)/
      tool = $1
      file = $3
      filepath = File.join(@workdir, file)
      if File.exist?(filepath)
        @created_resources << { tool: tool, file: filepath }
      end
    end

    # Match inline resource creation from stdout like "namespace/openshift-ptp created"
    if stdout =~ %r{^(\S+/\S+)\s+created}
      @created_resources << { resource: $1 }
    end
  end

  def run_cleanup
    puts "\n--- Cleanup ---"

    # Delete resources in reverse order
    @created_resources.reverse.each do |res|
      if res[:file]
        tool = res[:tool] || @cli_tool || 'oc'
        puts "Deleting resources from: #{res[:file]}"
        stdout, stderr, status = Open3.capture3("#{tool} delete -f #{res[:file]} --ignore-not-found")
        if status.success?
          puts "[CLEANED] #{stdout.strip}"
        else
          puts "[WARN] Cleanup failed: #{stderr.strip}"
        end
      elsif res[:resource]
        tool = @cli_tool || 'oc'
        puts "Deleting: #{res[:resource]}"
        stdout, stderr, status = Open3.capture3("#{tool} delete #{res[:resource]} --ignore-not-found")
        if status.success?
          puts "[CLEANED] #{stdout.strip}"
        else
          puts "[WARN] Cleanup failed: #{stderr.strip}"
        end
      end
    end

    # Remove the working directory
    FileUtils.rm_rf(@workdir)
    puts "[CLEANED] Removed working directory: #{@workdir}"
  end

  def summarize
    puts "\n" + "="*60
    puts "FINAL SUMMARY"
    puts "="*60

    passed = @results.count { |r| r[:status] == :passed }
    failed = @results.count { |r| r[:status] == :failed }

    puts "Total executable steps: #{@results.size}"
    puts "Passed: #{passed}"
    puts "Failed: #{failed}"

    if failed > 0
      puts "\nFailed steps:"
      @results.select { |r| r[:status] == :failed }.each do |result|
        puts "  - Step #{result[:step]}: #{result[:error]&.split("\n")&.first}"
      end
    end

    # Check if a global verification example was included
    unless @content.downcase.include?("verify") || @content.downcase.include?(".verification")
      puts "\n[ADVICE] Consider adding an end-to-end verification step to this procedure."
    end

    puts "="*60
    puts passed == @results.size ? "✓ All steps PASSED" : "✗ Some steps FAILED"
    puts "="*60
  end
end

# Execution
if ARGV.empty?
  puts "Usage: ruby verify_proc.rb [--cleanup] <file.adoc>"
  puts "  --cleanup  Delete created resources and working directory after verification"
  exit 1
end

cleanup = ARGV.delete('--cleanup')
file_path = ARGV[0]

unless file_path && File.exist?(file_path)
  puts "Error: File not found: #{file_path}"
  exit 1
end

ProcedureVerifier.new(file_path, cleanup: !!cleanup).run_verification
