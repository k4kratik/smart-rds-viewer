#!/usr/bin/env ruby

require 'net/http'
require 'json'
require 'digest'

# Configuration
REPO = "k4kratik/smart-rds-viewer"
VERSION = ARGV[0] || "1.0.0"
FORMULA_PATH = "Formula/smart-rds-viewer.rb"

def get_release_assets(version)
  # Ensure version has v prefix
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

def calculate_sha256(url)
  puts "📥 Downloading #{url}..."
  response = Net::HTTP.get_response(URI(url))
  
  if response.code == "200"
    Digest::SHA256.hexdigest(response.body)
  else
    puts "❌ Failed to download #{url}"
    exit 1
  end
end

def update_formula(version, assets)
  formula_content = File.read(FORMULA_PATH)
  
  # Update version
  formula_content.gsub!(/version "[\d.]+"/, "version \"#{version}\"")
  
  # Update SHA256 hashes for each asset
  assets.each do |asset|
    name = asset["name"]
    download_url = asset["browser_download_url"]
    sha256 = calculate_sha256(download_url)
    
    puts "✅ #{name}: #{sha256}"
    
    # Replace placeholder SHA256 with actual hash
    formula_content.gsub!("PLACEHOLDER_SHA256", sha256)
  end
  
  # Write updated formula
  File.write(FORMULA_PATH, formula_content)
  puts "✅ Formula updated with SHA256 hashes"
end

# Main execution
# Clean version for display (remove v prefix if present)
display_version = VERSION.start_with?('v') ? VERSION[1..-1] : VERSION
puts "🔧 Updating Homebrew formula for v#{display_version}"

assets = get_release_assets(VERSION)
if assets.empty?
  puts "❌ No assets found in release"
  exit 1
end

update_formula(display_version, assets)
puts "🎉 Formula updated successfully!" 