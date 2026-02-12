echo "⬇️ Downloading buf..."

mkdir -p "bin"
VERSION="1.64.0" && \
curl -sSL \
"https://github.com/bufbuild/buf/releases/download/v${VERSION}/buf-$(uname -s)-$(uname -m)" \
-o "bin/buf" && \
chmod +x "bin/buf"

echo "✅ buf $(bin/buf --version) is installed"