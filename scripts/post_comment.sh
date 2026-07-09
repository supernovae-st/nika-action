#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# post_comment.sh <body-file> <marker> — sticky upsert: find the PR comment
# carrying <marker> and PATCH it; otherwise POST a new one. One comment per
# marker forever — re-pushes edit, never spam. Requires GH_TOKEN with
# pull-requests:write and a pull_request event; anything else falls back to
# the step summary (handled by the caller).
set -euo pipefail

BODY_FILE="${1:?body file}"
MARKER="${2:?marker}"

PR_NUMBER="$(jq -r '.pull_request.number // empty' "${GITHUB_EVENT_PATH}")"
if [ -z "${PR_NUMBER}" ]; then
  echo "not a pull_request event — skipping comment (body in step summary)"
  exit 0
fi

REPO="${GITHUB_REPOSITORY}"
# collect ids into a variable first — `gh --paginate | head -1` can die on
# SIGPIPE (exit 141) under pipefail when head closes the pipe mid-page
ALL_IDS="$(gh api "repos/${REPO}/issues/${PR_NUMBER}/comments" \
  --paginate --jq ".[] | select(.body | contains(\"${MARKER}\")) | .id")"
EXISTING_ID="$(printf '%s\n' "${ALL_IDS}" | head -1)"

if [ -n "${EXISTING_ID}" ]; then
  gh api --method PATCH "repos/${REPO}/issues/comments/${EXISTING_ID}" \
    -F body=@"${BODY_FILE}" > /dev/null
  echo "updated comment ${EXISTING_ID} (sticky upsert)"
else
  gh api --method POST "repos/${REPO}/issues/${PR_NUMBER}/comments" \
    -F body=@"${BODY_FILE}" > /dev/null
  echo "posted new comment"
fi
