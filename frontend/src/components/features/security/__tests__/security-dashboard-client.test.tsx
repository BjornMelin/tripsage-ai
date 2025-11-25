/** @vitest-environment jsdom */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import {
  ActiveSessionsList,
  ConnectionsSummary,
  LocalTime,
  SecurityEventsList,
} from "../security-dashboard-client";

vi.mock("@/components/ui/use-toast");

beforeEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

function CreateDeferred<T>() {
  let resolve: ((value: T) => void) | undefined;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });

  return {
    promise,
    resolve(value: T) {
      if (!resolve) {
        throw new Error("Deferred resolve called before initialization");
      }
      resolve(value);
    },
  };
}

describe("LocalTime", () => {
  it("renders a formatted timestamp for valid ISO input", () => {
    const isoString = "2025-01-02T15:30:00.000Z";
    render(<LocalTime isoString={isoString} />);
    const rendered = screen.getByTitle(isoString);
    const content = rendered.textContent ?? "";
    expect(content).not.toBe("—");
    expect(content).not.toBe("Invalid date");
  });

  it("renders an error label for invalid input", () => {
    render(<LocalTime isoString="not-a-date" />);
    expect(screen.getByText("Invalid date")).toBeInTheDocument();
  });
});

describe("SecurityEventsList", () => {
  it("renders event details and risk label", () => {
    const riskColor = {
      high: "text-red-600",
      low: "text-green-600",
      medium: "text-yellow-600",
    };
    render(
      <SecurityEventsList
        events={[
          {
            description: "Suspicious login",
            device: "Chrome",
            id: "evt-1",
            ipAddress: "1.1.1.1",
            riskLevel: "high",
            timestamp: "2025-01-02T00:00:00Z",
            type: "suspicious_activity",
          },
        ]}
        riskColor={riskColor}
      />
    );

    expect(screen.getByText("Suspicious login")).toBeInTheDocument();
    expect(screen.getByText("high")).toHaveClass("text-red-600");
    expect(screen.getByText("1.1.1.1")).toBeInTheDocument();
  });
});

describe("ConnectionsSummary", () => {
  it("renders metrics and last login", () => {
    render(
      <ConnectionsSummary
        metrics={{
          activeSessions: 2,
          failedLoginAttempts: 0,
          lastLogin: "2025-01-02T10:00:00Z",
          oauthConnections: ["google", "github"],
          securityScore: 95,
          trustedDevices: 3,
        }}
      />
    );

    expect(screen.getByText(/Last login:/i)).toBeInTheDocument();
    expect(screen.getByText("OAuth: google, github")).toBeInTheDocument();
    expect(screen.getByText("Trusted devices: 3")).toBeInTheDocument();
  });
});

describe("ActiveSessionsList", () => {
  const successResponse = { json: async () => ({}), ok: true } as Response;
  const failureResponse = {
    json: async () => ({}),
    ok: false,
    status: 500,
  } as Response;

  it("terminates a non-current session and removes it from the list", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(successResponse);
    const { toast } = await import("@/components/ui/use-toast");
    const sessions = [
      {
        browser: "Chrome",
        device: "Laptop",
        id: "sess-1",
        ipAddress: "2.2.2.2",
        isCurrent: false,
        lastActivity: "2025-01-02T12:00:00Z",
        location: "NYC",
      },
      {
        browser: "Safari",
        device: "Phone",
        id: "sess-2",
        ipAddress: "3.3.3.3",
        isCurrent: true,
        lastActivity: "2025-01-02T12:00:00Z",
        location: "NYC",
      },
    ];

    render(<ActiveSessionsList sessions={sessions} />);

    await userEvent.click(screen.getByRole("button", { name: "Terminate" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/security/sessions/sess-1", {
        method: "DELETE",
      });
    });

    await waitFor(() => {
      expect(screen.queryByText("Laptop")).not.toBeInTheDocument();
    });

    expect(toast).toHaveBeenCalledWith({
      description: "The selected session has been revoked.",
      title: "Session terminated",
    });
  });

  it("shows an error toast when termination fails", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(failureResponse);
    const { toast } = await import("@/components/ui/use-toast");
    const sessions = [
      {
        browser: "Chrome",
        device: "Laptop",
        id: "sess-1",
        ipAddress: "2.2.2.2",
        isCurrent: false,
        lastActivity: "2025-01-02T12:00:00Z",
        location: "NYC",
      },
    ];

    render(<ActiveSessionsList sessions={sessions} />);

    const terminateButton = screen.getByRole("button", { name: "Terminate" });
    await userEvent.click(terminateButton);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    expect(toast).toHaveBeenCalledWith({
      description: "Failed to terminate session (500)",
      title: "Unable to terminate session",
      variant: "destructive",
    });
    expect(screen.getByText("Laptop")).toBeInTheDocument();
  });

  it("disables the terminate button while the request is pending", async () => {
    const deferredFetch = CreateDeferred<Response>();
    vi.spyOn(globalThis, "fetch").mockReturnValue(deferredFetch.promise);

    const sessions = [
      {
        browser: "Chrome",
        device: "Laptop",
        id: "sess-1",
        ipAddress: "2.2.2.2",
        isCurrent: false,
        lastActivity: "2025-01-02T12:00:00Z",
        location: "NYC",
      },
    ];

    render(<ActiveSessionsList sessions={sessions} />);

    const terminateButton = screen.getByRole("button", { name: "Terminate" });
    await userEvent.click(terminateButton);

    expect(terminateButton).toBeDisabled();

    deferredFetch.resolve(successResponse);

    await waitFor(() => {
      expect(
        screen.queryByRole("button", { name: "Terminate" })
      ).not.toBeInTheDocument();
    });
  });
});
