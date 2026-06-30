class Speekify < Formula
  desc "Auto-detecting text and URL to WAV converter powered by Supertonic v3"
  homepage "https://github.com/OtterlySpaceLabs/speekify"
  url "https://github.com/OtterlySpaceLabs/speekify/releases/download/v0.1.2/speekify-macos-arm64.tar.gz"
  sha256 "1b3ad11e4721d543e692a1354ff636becf4b7c6bd52c6e950064953a1da15215"
  version "0.1.2"

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
    assert_match "0.1.2", shell_output("#{bin}/speekify --version")
    assert_match "Download and warm up", shell_output("#{bin}/speekify setup --help")
    assert_predicate man1/"speekify.1", :exist?
  end
end
