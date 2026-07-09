#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# install_nika.sh <version> — download the pinned nika release for this
# runner's platform, VERIFY it against the release's published SHA256SUMS
# (an unverified curl|tar into CI is the supply-chain hole this action
# refuses to ship), install into RUNNER_TEMP, append to GITHUB_PATH.
set -euo pipefail

VERSION="${1:?usage: install_nika.sh <version, e.g. 0.98.0>}"

case "$(uname -s)/$(uname -m)" in
  Linux/x86_64)   PLATFORM="linux-x64" ;;
  Linux/aarch64)  PLATFORM="linux-arm64" ;;
  Darwin/arm64)   PLATFORM="macos-arm64" ;;
  Darwin/x86_64)  PLATFORM="macos-x64" ;;
  *) echo "::error::unsupported runner platform: $(uname -s)/$(uname -m)"; exit 1 ;;
esac

ASSET="nika-${PLATFORM}-${VERSION}.tar.gz"
BASE="https://github.com/supernovae-st/nika/releases/download/v${VERSION}"
DEST="${RUNNER_TEMP:-/tmp}/nika-bin"
mkdir -p "${DEST}"
cd "${DEST}"

curl -fsSL --retry 3 "${BASE}/${ASSET}" -o "${ASSET}"
curl -fsSL --retry 3 "${BASE}/SHA256SUMS" -o SHA256SUMS

# verify: exact line for our asset, checked with whatever checksum tool the
# runner has (linux: sha256sum · macos: shasum -a 256)
grep " ${ASSET}\$" SHA256SUMS > expected.sums
if command -v sha256sum > /dev/null; then
  sha256sum -c expected.sums
else
  shasum -a 256 -c expected.sums
fi

tar xzf "${ASSET}"
chmod +x nika
echo "${DEST}" >> "${GITHUB_PATH:-/dev/null}"
echo "installed nika ${VERSION} (${PLATFORM}) → ${DEST}/nika (SHA256 verified)"
"${DEST}/nika" --version
