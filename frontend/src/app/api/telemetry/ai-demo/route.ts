import { NextResponse } from "next/server";
import { emitOperationalAlert } from "@/lib/telemetry/alerts";

type TelemetryPayload = {
  detail?: string;
  status: "success" | "error";
};

export async function POST(req: Request): Promise<Response> {
  try {
    const body = (await req.json()) as TelemetryPayload;
    if (body.status !== "success" && body.status !== "error") {
      return NextResponse.json({ ok: false }, { status: 400 });
    }

    emitOperationalAlert("ai_demo.stream", {
      attributes: {
        detail: body.detail ?? null,
        status: body.status,
      },
      severity: body.status === "error" ? "warning" : "info",
    });
    return NextResponse.json({ ok: true });
  } catch {
    return NextResponse.json({ ok: false }, { status: 400 });
  }
}
