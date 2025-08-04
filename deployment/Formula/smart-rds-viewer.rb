class SmartRdsViewer < Formula
  desc "Your terminal companion for monitoring Amazon RDS instances with real-time data, pricing, and interactive insights"
  homepage "https://github.com/k4kratik/smart-rds-viewer"
  version "0.0.18"
  
  on_macos do
    if Hardware::CPU.arm?
      url "https://github.com/k4kratik/smart-rds-viewer/releases/download/v#{version}/smart-rds-viewer-macos"
      sha256 "PLACEHOLDER_SHA256" # This will be updated by the workflow
    else
      url "https://github.com/k4kratik/smart-rds-viewer/releases/download/v#{version}/smart-rds-viewer-macos"
      sha256 "PLACEHOLDER_SHA256" # This will be updated by the workflow
    end
  end

  on_linux do
    if Hardware::CPU.arm?
      url "https://github.com/k4kratik/smart-rds-viewer/releases/download/v#{version}/smart-rds-viewer-linux-arm64"
      sha256 "PLACEHOLDER_SHA256" # This will be updated by the workflow
    else
      url "https://github.com/k4kratik/smart-rds-viewer/releases/download/v#{version}/smart-rds-viewer-linux-amd64"
      sha256 "PLACEHOLDER_SHA256" # This will be updated by the workflow
    end
  end

  def install
    if OS.mac?
      bin.install "smart-rds-viewer-macos" => "smart-rds-viewer"
    else
      bin.install "smart-rds-viewer-linux-#{Hardware::CPU.arm? ? "arm64" : "amd64"}" => "smart-rds-viewer"
    end
  end

  test do
    system "#{bin}/smart-rds-viewer", "--help"
  end
end 