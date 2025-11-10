import { zodResolver } from "@hookform/resolvers/zod";
import { render } from "@testing-library/react";
import React from "react";
import { useForm } from "react-hook-form";
import { describe, expect, it } from "vitest";
import { z } from "zod";

function FormHarness() {
  const schema = z.object({ email: z.string().email() });
  const { handleSubmit, register } = useForm<{ email: string }>({
    resolver: zodResolver(schema),
  });
  const onSubmit = () => {
    // Empty submit handler for test
  };
  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input type="email" {...register("email")} defaultValue="a@b.com" />
      <button type="submit">Submit</button>
    </form>
  );
}

describe("zod v4 resolver interop", () => {
  it("mounts a form with zodResolver without runtime errors", () => {
    const { getByText } = render(React.createElement(FormHarness));
    expect(getByText("Submit")).toBeInTheDocument();
  });
});
