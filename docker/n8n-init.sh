#!/bin/sh
# Bootstraps the local n8n instance the first time the n8n_data volume is used:
# imports the two Header-Auth credentials (values come from the root .env, so no
# secret is ever committed), imports the workflow exports from workflows/n8n and
# publishes all four workflows: the three that Django and the orchestrator call
# by webhook, plus the research collector with its daily schedule trigger.
#
# Runs once per volume. To bootstrap again, delete the marker
# (docker compose exec n8n rm /home/node/.n8n/.bootstrapped) or wipe the volume
# with `docker compose down -v`. Re-importing overwrites edits made in the editor.

MARKER=/home/node/.n8n/.bootstrapped
WORKFLOW_DIR=/workflows
PUBLISHED="MissionGeneratorV2Prod MissionWorkerV2Prod RsrchSelect2026A RsrchCollect2026"

bootstrap() {
    credentials=$(mktemp) || return 1
    # The workflow exports reference these credential ids, so creating the
    # credentials under the same ids wires up every node without reassignment.
    node -e '
        const fs = require("fs");
        fs.writeFileSync(process.argv[1], JSON.stringify([
            {
                id: "VKHohALUbaf2u4a3",
                name: "Django n8n Service Secret",
                type: "httpHeaderAuth",
                data: {name: "X-N8N-Service-Secret", value: process.env.N8N_SERVICE_SECRET || ""},
            },
            {
                id: "T7OO5sQEPVKyuyym",
                name: "KIconnect API",
                type: "httpHeaderAuth",
                data: {name: "Authorization", value: "Bearer " + (process.env.KICONNECT_API_KEY || "")},
            },
        ]));
    ' "$credentials" || { rm -f "$credentials"; return 1; }
    n8n import:credentials --input="$credentials" || { rm -f "$credentials"; return 1; }
    rm -f "$credentials"

    for workflow in "$WORKFLOW_DIR"/*.json; do
        n8n import:workflow --input="$workflow" || return 1
    done

    # Importing leaves a workflow unpublished, so publish afterwards.
    for id in $PUBLISHED; do
        n8n publish:workflow --id="$id" || return 1
    done
}

if [ ! -f "$MARKER" ]; then
    if bootstrap; then
        touch "$MARKER"
        echo "n8n bootstrap complete: credentials imported, workflows published."
    else
        echo "n8n bootstrap failed. Create the owner account at http://localhost:5678," \
             "then run: docker compose restart n8n"
    fi
fi

exec /docker-entrypoint.sh start
