class MetisKb < Formula
  desc "Terminal knowledge base for commands, code snippets, and SQL queries"
  homepage "https://github.com/abyssnlp/metis"
  url "https://files.pythonhosted.org/packages/source/m/metis-kb/metis_kb-0.1.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  version "0.1.0"
  license "MIT"

  depends_on "python@3.12"

  # Dependencies are installed via pip into a Homebrew-managed virtualenv so
  # they are fully isolated from the system Python and other formulae.
  def install
    venv = virtualenv_create(libexec, "python3")
    venv.pip_install "metis-kb==#{version}"
    bin.install_symlink libexec/"bin/metis"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/metis -V")
  end
end
