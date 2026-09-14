import { NextRequest, NextResponse } from "next/server";
import { listFindings } from "@/lib/findings";

// Forwards a client-triggered "load more" page request to FastAPI. The
// only place a route handler is used instead of a Server Action in this
// phase — it's a client-initiated paginated GET, not a mutation.
export async function GET(request: NextRequest) {
  const competitorId = request.nextUrl.searchParams.get("competitor_id") ?? undefined;
  const cursor = request.nextUrl.searchParams.get("cursor") ?? undefined;

  const result = await listFindings({ competitorId, cursor });
  return NextResponse.json(result);
}
