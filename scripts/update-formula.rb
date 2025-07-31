#!/usr/bin/env ruby

require 'net/http'
require 'json'
require 'digest'

# Configuration
REPO = "k4kratik/smart-rds-viewer"
VERSION = ARGV[0] || "1.0.0"
FORMULA_PATH = "Formula/smart-rds-viewer.rb"

# Helper to follow redirects (e.g., GitHub asset links)
def fetch_with_redirect(uri_str, limit = 10)
  raise ArgumentError, 'Too many HTTP redirects' if limit == 0

  uri = URI(uri_str)
  response = Net::HTTP.get_response(uri)

  case response
  when Net::HTTPSuccess
    return response.body
  when Net::HTTPRedirection
    location = response['location']
    warn "🔁 Redirected to #{location}"
    fetch_with_redirect(location, limit - 1)
  else
    raise "HTTP Error: #{response.code} for #{uri_str}"
  end
end

# Download the asset and compute SHA256
def calculate_sha256(url)
  puts "📥 Downloading #{url}..."
  begin
    body = fetch_with_redirect(url)
    Digest::SHA256.hexdigest(body)
  rescue => e
    puts "❌ Failed to download #{url}: #{e.message}"
    exit 1
  end
end

# Get GitHub release assets
def get_release_assets(version)
  version_with_v = version.start_with?('v') ? version : "v#{version}"
  url = "https://api.github.com/repos/#{REPO}/releases/tags/#{version_with_v}"
  response = Net::HTTP.get_response(URI(url))
  
  if response.code == "200"
    data = JSON.parse(response.body)
    data["assets"]
  else
    puts "❌ Failed to get release info for #{version_with_v}"
    exit 1
  end
end

# Update Homebrew formula
def update_formula(version, assets)
  formula_content = File.read(FORMULA_PATH)

  # Update version
  formula_content.gsub!(/version "[\d.]+"|version '([\d.]*)'/, "version \"#{version}\"")

  # Update SHA256 hashes for each asset
  assets.each do |asset|
    name = asset["name"]
    download_url = asset["browser_download_url"]
    sha256 = calculate_sha256(download_url)

    puts "✅ #{name}: #{sha256}"

    # Replace placeholder or old sha256 for this asset
    # This assumes a line like: sha256 "..." # smart-rds-viewer-linux-amd64
    formula_content.gsub!(/sha256\s+"[a-f0-9]+"(\s+#\s*#{name})?/, "sha256 \"#{sha256}\" # #{name}")
  end

  # Write back updated formula
  File.write(FORMULA_PATH, formula_content)
  puts "✅ Formula updated with SHA256 hashes"
end

# Main
display_version = VERSION.start_with?('v') ? VERSION[1..-1] : VERSION
puts "🔧 Updating Homebrew formula for v#{display_version}"

assets = get_release_assets(VERSION)
if assets.empty?
  puts "❌ No assets found in release"
  exit 1
end

update_formula(display_version, assets)
puts "🎉 Formula updated successfully!"
