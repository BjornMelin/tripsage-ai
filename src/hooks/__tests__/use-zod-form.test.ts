/** @vitest-environment jsdom */

import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { createFakeTimersContext } from "@/test/utils/with-fake-timers";
import { useZodForm } from "../use-zod-form";

describe("useZodForm", () => {
  const timers = createFakeTimersContext({ shouldAdvanceTime: true });
  const nowIso = "2026-01-15T12:00:00.000Z";
  const schema = z.object({
    title: z.string().min(3, { error: "Title must be at least 3 characters" }),
  });

  beforeEach(() => {
    timers.setup();
    vi.setSystemTime(new Date(nowIso));
  });

  afterEach(timers.teardown);

  it("validates with trigger() and exposes field errors", async () => {
    const { result } = renderHook(() =>
      useZodForm({
        defaultValues: { title: "" },
        mode: "onChange",
        schema,
      })
    );

    act(() => {
      result.current.register("title");
    });

    let isValid = false;
    await act(async () => {
      isValid = await result.current.trigger();
    });

    expect(isValid).toBe(false);
    expect(result.current.getFieldState("title").error?.message).toBe(
      "Title must be at least 3 characters"
    );
    expect(result.current.isFormComplete).toBe(false);
  });

  it("updates isFormComplete when the form becomes valid", async () => {
    const { result } = renderHook(() => {
      const form = useZodForm({
        defaultValues: { title: "" },
        mode: "onChange",
        schema,
      });

      return {
        form,
        isFormComplete: form.isFormComplete,
      };
    });

    act(() => {
      result.current.form.register("title");
      result.current.form.setValue("title", "Trip");
    });

    let isValid = false;
    await act(async () => {
      isValid = await result.current.form.trigger();
    });

    expect(isValid).toBe(true);
    expect(result.current.isFormComplete).toBe(true);
  });

  it("handleSubmitSafe calls onInvalid with a ValidationResult and populates validationState", async () => {
    const { result } = renderHook(() =>
      useZodForm({
        defaultValues: { title: "" },
        mode: "onChange",
        schema,
      })
    );

    act(() => {
      result.current.register("title");
    });

    const onValid = vi.fn();
    const onInvalid = vi.fn();

    await act(async () => {
      await result.current.handleSubmitSafe(onValid, onInvalid)();
    });

    expect(onValid).not.toHaveBeenCalled();
    expect(onInvalid).toHaveBeenCalledTimes(1);

    const [validationResult] = onInvalid.mock.calls[0] ?? [];
    expect(validationResult).toMatchObject({
      success: false,
    });
    expect(validationResult.errors?.[0]).toMatchObject({
      context: "form",
      field: "title",
      message: "Title must be at least 3 characters",
      timestamp: new Date(nowIso),
    });

    expect(result.current.validationState.validationErrors).toContain(
      "Title must be at least 3 characters"
    );
    expect(result.current.validationState.lastValidation).toEqual(new Date(nowIso));
  });

  it("handleSubmitSafe applies transformSubmitData and clears validation errors on success", async () => {
    const { result } = renderHook(() =>
      useZodForm({
        defaultValues: { title: "" },
        mode: "onChange",
        schema,
        transformSubmitData: (data) => ({ ...data, title: data.title.trim() }),
      })
    );

    act(() => {
      result.current.register("title");
      result.current.setValue("title", "  Trip  ");
    });

    const onSubmit = vi.fn();

    await act(async () => {
      await result.current.handleSubmitSafe((data) => {
        onSubmit(data);
        expect(data).toEqual({ title: "Trip" });
      })();
    });

    expect(onSubmit).toHaveBeenCalledWith({ title: "Trip" });
    expect(result.current.validationState.validationErrors).toHaveLength(0);
    expect(result.current.validationState.lastValidation).toEqual(new Date(nowIso));
  });
});
