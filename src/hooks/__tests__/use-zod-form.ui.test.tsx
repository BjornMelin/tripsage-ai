/** @vitest-environment jsdom */

import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { z } from "zod";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { render, screen, waitFor } from "@/test/test-utils";
import { useZodForm } from "../use-zod-form";

const schema = z.object({
  title: z.string().min(3, { error: "Title must be at least 3 characters" }),
});

type TestFormValues = z.infer<typeof schema>;

function TestForm({
  onSubmit,
}: {
  onSubmit: (data: TestFormValues) => void | Promise<void>;
}) {
  const form = useZodForm({
    defaultValues: { title: "" },
    mode: "onChange",
    schema,
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmitSafe(onSubmit)}>
        <FormField
          control={form.control}
          name="title"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Title</FormLabel>
              <FormControl>
                <input aria-label="Title" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <button type="submit">Submit</button>
      </form>
    </Form>
  );
}

describe("useZodForm (UI integration)", () => {
  it("renders FormMessage on invalid submit and submits once valid", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    render(<TestForm onSubmit={onSubmit} />);

    await user.click(screen.getByRole("button", { name: "Submit" }));
    expect(screen.getByText("Title must be at least 3 characters")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText("Title"), "Trip");

    // Verify validation message disappears after entering valid data
    await waitFor(() => {
      expect(
        screen.queryByText("Title must be at least 3 characters")
      ).not.toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Submit" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit).toHaveBeenCalledWith({ title: "Trip" });
  });
});
