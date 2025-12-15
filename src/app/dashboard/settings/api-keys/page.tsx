/**
 * @fileoverview Dashboard API keys management page (route wrapper).
 *
 * Renders the shared API keys UI while allowing this route group to own its page
 * boundaries (metadata/layout) independently.
 */

import { ApiKeysContent } from "@/components/settings/api-keys-content";

export default function ApiKeysPage() {
  return <ApiKeysContent />;
}
