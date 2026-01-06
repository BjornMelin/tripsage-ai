/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import {
  type DestinationSearchFormValues,
  mapDestinationValuesToParams,
} from "../destination-search-form";

describe("mapDestinationValuesToParams", () => {
  it("converts form values to search params", () => {
    const formValues: DestinationSearchFormValues = {
      language: "fr",
      limit: 7,
      query: "Paris",
      region: "eu",
      types: ["locality", "establishment"],
    };

    expect(mapDestinationValuesToParams(formValues)).toEqual({
      language: "fr",
      limit: 7,
      query: "Paris",
      region: "eu",
      types: ["locality", "establishment"],
    });
  });
});
