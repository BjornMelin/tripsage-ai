import "server-only";

import { redirect } from "next/navigation";

export default function SecuritySettingsRedirect() {
  redirect("/security");
}
