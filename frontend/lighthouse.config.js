module.exports = {
  ci: {
    assert: {
      assertions: {
        "categories:accessibility": ["error", { minScore: 0.9 }],
        "categories:best-practices": ["warn", { minScore: 0.85 }],
        "categories:performance": ["warn", { minScore: 0.8 }],
        "categories:seo": ["warn", { minScore: 0.85 }],
        "cumulative-layout-shift": ["warn", { maxNumericValue: 0.1 }],
        "first-contentful-paint": ["warn", { maxNumericValue: 2000 }],
        "largest-contentful-paint": ["warn", { maxNumericValue: 2500 }],
        "total-blocking-time": ["warn", { maxNumericValue: 300 }],
      },
    },
    collect: {
      numberOfRuns: 3,
      settings: {
        preset: "desktop",
        throttling: {
          cpuSlowdownMultiplier: 1,
        },
      },
      url: ["http://localhost:3000"],
    },
    upload: {
      target: "temporary-public-storage",
    },
  },
};
