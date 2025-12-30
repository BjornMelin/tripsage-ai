/**
 * @fileoverview Pagination slice for the search results store.
 */

import type { StateCreator } from "zustand";
import type { SearchResultsState } from "../types";

type SearchResultsPaginationSlice = Pick<
  SearchResultsState,
  "nextPage" | "previousPage" | "setPage" | "setResultsPerPage"
>;

export const createSearchResultsPaginationSlice: StateCreator<
  SearchResultsState,
  [],
  [],
  SearchResultsPaginationSlice
> = (set, get) => ({
  nextPage: () => {
    const { pagination } = get();
    if (pagination.hasNextPage) {
      get().setPage(pagination.currentPage + 1);
    }
  },

  previousPage: () => {
    const { pagination } = get();
    if (pagination.hasPreviousPage) {
      get().setPage(pagination.currentPage - 1);
    }
  },

  setPage: (page) => {
    const { pagination } = get();
    const validPage = Math.max(1, Math.min(pagination.totalPages, page));

    set({
      pagination: {
        ...pagination,
        currentPage: validPage,
        hasNextPage: validPage < pagination.totalPages,
        hasPreviousPage: validPage > 1,
      },
    });
  },

  setResultsPerPage: (perPage) => {
    const { pagination } = get();
    const validPerPage = Math.max(1, Math.min(100, perPage));
    const totalPages = Math.ceil(pagination.totalResults / validPerPage);
    const currentPage = Math.min(pagination.currentPage, totalPages);

    set({
      pagination: {
        ...pagination,
        currentPage: Math.max(1, currentPage),
        hasNextPage: currentPage < totalPages,
        hasPreviousPage: currentPage > 1,
        resultsPerPage: validPerPage,
        totalPages,
      },
    });
  },
});
