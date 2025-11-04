import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAsyncLoading, useDebouncedLoading, useLoading } from "../use-loading";

describe("useLoading", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("initializes with default state", () => {
    const { result } = renderHook(() => useLoading());

    expect(result.current.isLoading).toBe(false);
    expect(result.current.message).toBeUndefined();
    expect(result.current.progress).toBeUndefined();
    expect(result.current.error).toBeUndefined();
  });

  it("initializes with custom initial state", () => {
    const { result } = renderHook(() =>
      useLoading({
        initialLoading: true,
        initialMessage: "Initial loading...",
      })
    );

    expect(result.current.isLoading).toBe(true);
    expect(result.current.message).toBe("Initial loading...");
  });

  it("starts loading", () => {
    const { result } = renderHook(() => useLoading());

    act(() => {
      result.current.startLoading("Loading data...");
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.message).toBe("Loading data...");
    expect(result.current.error).toBeUndefined();
  });

  it("stops loading", () => {
    const { result } = renderHook(() => useLoading());

    act(() => {
      result.current.startLoading();
    });

    expect(result.current.isLoading).toBe(true);

    act(() => {
      result.current.stopLoading();
    });

    expect(result.current.isLoading).toBe(false);
  });

  it("sets progress", () => {
    const { result } = renderHook(() => useLoading());

    act(() => {
      result.current.setProgress(50);
    });

    expect(result.current.progress).toBe(50);
  });

  it("clamps progress between 0 and 100", () => {
    const { result } = renderHook(() => useLoading());

    act(() => {
      result.current.setProgress(-10);
    });
    expect(result.current.progress).toBe(0);

    act(() => {
      result.current.setProgress(150);
    });
    expect(result.current.progress).toBe(100);
  });

  it("sets message", () => {
    const { result } = renderHook(() => useLoading());

    act(() => {
      result.current.setMessage("New message");
    });

    expect(result.current.message).toBe("New message");
  });

  it("sets error and stops loading", () => {
    const { result } = renderHook(() => useLoading());

    act(() => {
      result.current.startLoading();
    });

    expect(result.current.isLoading).toBe(true);

    act(() => {
      result.current.setError("Something went wrong");
    });

    expect(result.current.error).toBe("Something went wrong");
    expect(result.current.isLoading).toBe(false);
  });

  it("clears error", () => {
    const { result } = renderHook(() => useLoading());

    act(() => {
      result.current.setError("Error message");
    });

    expect(result.current.error).toBe("Error message");

    act(() => {
      result.current.clearError();
    });

    expect(result.current.error).toBeUndefined();
  });

  it("resets state", () => {
    const { result } = renderHook(() => useLoading());

    act(() => {
      result.current.startLoading("Loading...");
      result.current.setProgress(75);
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.message).toBe("Loading...");
    expect(result.current.progress).toBe(75);

    act(() => {
      result.current.reset();
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.message).toBeUndefined();
    expect(result.current.progress).toBeUndefined();
    expect(result.current.error).toBeUndefined();
  });

  it("handles timeout", () => {
    const onTimeout = vi.fn();
    const { result } = renderHook(() => useLoading({ onTimeout, timeout: 5000 }));

    act(() => {
      result.current.startLoading();
    });

    expect(result.current.isLoading).toBe(true);

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(result.current.isLoading).toBe(false);
    expect(onTimeout).toHaveBeenCalledTimes(1);
  });

  it("clears timeout when stopped manually", () => {
    const onTimeout = vi.fn();
    const { result } = renderHook(() => useLoading({ onTimeout, timeout: 5000 }));

    act(() => {
      result.current.startLoading();
    });

    act(() => {
      result.current.stopLoading();
    });

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(onTimeout).not.toHaveBeenCalled();
  });
});

describe("useAsyncLoading", () => {
  it("initializes with default state", () => {
    const asyncFn = vi.fn().mockResolvedValue("result");
    const { result } = renderHook(() => useAsyncLoading(asyncFn));

    expect(result.current.data).toBeUndefined();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeUndefined();
  });

  it("handles successful execution", async () => {
    const asyncFn = vi.fn().mockResolvedValue("success");
    const { result } = renderHook(() => useAsyncLoading(asyncFn));

    let promise: Promise<unknown>;
    act(() => {
      promise = result.current.execute("arg1", "arg2");
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.error).toBeUndefined();

    await act(async () => {
      const resultValue = await promise;
      expect(resultValue).toBe("success");
    });

    expect(result.current.data).toBe("success");
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeUndefined();
    expect(asyncFn).toHaveBeenCalledWith("arg1", "arg2");
  });

  it("handles failed execution", async () => {
    const error = new Error("Test error");
    const asyncFn = vi.fn().mockRejectedValue(error);
    const { result } = renderHook(() => useAsyncLoading(asyncFn));

    let promise: Promise<unknown>;
    act(() => {
      promise = result.current.execute();
    });

    expect(result.current.isLoading).toBe(true);

    await act(async () => {
      try {
        await promise;
      } catch (e) {
        expect(e).toBe(error);
      }
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe("Test error");
    expect(result.current.data).toBeUndefined();
  });

  it("resets state", async () => {
    const asyncFn = vi.fn().mockResolvedValue("data");
    const { result } = renderHook(() => useAsyncLoading(asyncFn));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.data).toBe("data");

    act(() => {
      result.current.reset();
    });

    expect(result.current.data).toBeUndefined();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeUndefined();
  });
});

describe("useDebouncedLoading", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("debounces start loading", () => {
    const { result } = renderHook(() => useDebouncedLoading(300));

    act(() => {
      result.current.startLoading("Loading...");
    });

    // Should not be loading immediately
    expect(result.current.isLoading).toBe(false);

    act(() => {
      vi.advanceTimersByTime(300);
    });

    // Should be loading after debounce delay
    expect(result.current.isLoading).toBe(true);
    expect(result.current.message).toBe("Loading...");
  });

  it("debounces stop loading", () => {
    const { result } = renderHook(() => useDebouncedLoading(300));

    // Start loading manually to set initial state
    act(() => {
      result.current.startLoading();
      vi.advanceTimersByTime(300);
    });

    expect(result.current.isLoading).toBe(true);

    act(() => {
      result.current.stopLoading();
    });

    // Should still be loading immediately
    expect(result.current.isLoading).toBe(true);

    act(() => {
      vi.advanceTimersByTime(300);
    });

    // Should stop loading after debounce delay
    expect(result.current.isLoading).toBe(false);
  });

  it("cancels previous debounced call", () => {
    const { result } = renderHook(() => useDebouncedLoading(300));

    act(() => {
      result.current.startLoading("First");
    });

    act(() => {
      vi.advanceTimersByTime(200);
    });

    act(() => {
      result.current.startLoading("Second");
    });

    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.message).toBe("Second");
  });
});
