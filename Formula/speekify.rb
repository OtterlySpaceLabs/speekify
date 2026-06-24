class Speekify < Formula
  desc "French text and URL to WAV converter powered by Supertonic v3"
  homepage "https://github.com/OtterlySpaceLabs/speekify"
  url "https://github.com/OtterlySpaceLabs/speekify/releases/download/v0.1.1/speekify-macos-arm64.tar.gz"
  sha256 "e42c2f6b1cb4906bcfbd7d929297f8fa953b3efd9145a75dff23ae4b379f53da"
  version "0.1.1"

  def install
    # onedir build: the launcher needs its sibling _internal/ folder,
    # so install the whole dir into libexec and symlink the launcher.
    libexec.install "speekify"
    bin.install_symlink libexec/"speekify/speekify"
    man1.install "share/man/man1/speekify.1"
  end

  test do
    assert_match "Generate a local WAV file", shell_output("#{bin}/speekify --help")
    assert_match "speekify --doctor", shell_output("#{bin}/speekify --help")
    assert_match "0.1.1", shell_output("#{bin}/speekify --version")
    assert_match "Download and warm up", shell_output("#{bin}/speekify setup --help")
    assert_predicate man1/"speekify.1", :exist?
  end
end
