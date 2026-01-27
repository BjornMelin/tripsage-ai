/**
 * @fileoverview Marketing homepage composition for TripSage AI.
 */

import {
  ArrowRightIcon,
  CalendarIcon,
  CheckIcon,
  CompassIcon,
  MapPinIcon,
  ShieldIcon,
  SparklesIcon,
  WalletIcon,
} from "lucide-react";
import Link from "next/link";
import {
  MARKETING_CONTAINER_CLASS,
  MarketingContainer,
} from "@/components/marketing/marketing-container";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CurrentYear } from "@/components/ui/current-year";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { MAIN_CONTENT_ID } from "@/lib/a11y/landmarks";
import { ROUTES } from "@/lib/routes";
import { cn } from "@/lib/utils";

type FeatureCard = {
  description: string;
  href: string;
  highlights?: readonly string[];
  icon: typeof SparklesIcon;
  title: string;
  variant: "bento" | "card";
};

const FEATURE_CARDS = [
  {
    description:
      "Describe the vibe, constraints, and must‑dos. TripSage turns it into an itinerary you can refine.",
    highlights: ["Day-by-day structure", "Editable options", "Shareable output"],
    href: ROUTES.aiDemo,
    icon: SparklesIcon,
    title: "AI itinerary builder",
    variant: "bento",
  },
  {
    description:
      "Set a budget and tradeoffs. Keep the plan realistic with clear price expectations and options.",
    highlights: ["Budget ranges", "Tradeoff hints", "Cost drivers"],
    href: ROUTES.aiDemo,
    icon: WalletIcon,
    title: "Budget guardrails",
    variant: "bento",
  },
  {
    description:
      "Turn your itinerary into a schedule-ready plan built for real travel days and time blocks.",
    href: ROUTES.aiDemo,
    icon: CalendarIcon,
    title: "Calendar-ready planning",
    variant: "card",
  },
  {
    description:
      "Get smarter routes and neighborhood choices so you explore more and commute less.",
    href: ROUTES.aiDemo,
    icon: MapPinIcon,
    title: "Location-aware suggestions",
    variant: "card",
  },
  {
    description:
      "Clear assumptions, transparent choices, and an exportable plan, no black-box travel magic.",
    href: ROUTES.faq,
    icon: ShieldIcon,
    title: "Built for trust",
    variant: "card",
  },
  {
    description:
      "Start with a quick draft, then iterate. Add constraints, swap activities, and lock the final trip.",
    href: ROUTES.aiDemo,
    icon: CompassIcon,
    title: "Fast iteration",
    variant: "card",
  },
] satisfies readonly FeatureCard[];

const STEPS = [
  {
    description:
      "Tell TripSage where you’re going, when, and what you care about, pace, food, budget, and priorities.",
    icon: MapPinIcon,
    title: "Set your constraints",
  },
  {
    description:
      "Get a structured plan with daily flow, optional upgrades, and clear alternatives when tradeoffs pop up.",
    icon: SparklesIcon,
    title: "Generate a plan",
  },
  {
    description:
      "Refine the itinerary collaboratively, then keep it handy for the trip, simple, organized, and flexible.",
    icon: CalendarIcon,
    title: "Polish and go",
  },
] as const;

const TRUST_MARKS = ["Next.js", "Supabase", "Stripe", "Amadeus", "Upstash"] as const;

const TRUST_MARK_DESCRIPTIONS: Record<(typeof TRUST_MARKS)[number], string> = {
  Amadeus: "Travel inventory and pricing.",
  "Next.js": "Fast app routing + server rendering.",
  Stripe: "Secure payments and billing.",
  Supabase: "Auth + Postgres + realtime data.",
  Upstash: "Rate limiting + background tasks.",
};

const QUICK_CHECKS = [
  "Structured daily plan",
  "Budget-aware tradeoffs",
  "Clear, editable output",
] as const;

const TESTIMONIALS = [
  {
    body: "The day-by-day plan keeps options open without losing structure. Swapping activities doesn’t break the itinerary.",
    initials: "NK",
    label: "Trips",
    name: "Noah K.",
    role: "Frequent traveler",
  },
  {
    body: "Budget tradeoffs are obvious. I can see what’s driving cost and choose the version of the trip that fits.",
    initials: "AR",
    label: "Budgets",
    name: "Ava R.",
    role: "Weekend planner",
  },
] as const;

export function MarketingHome() {
  return (
    <>
      <main id={MAIN_CONTENT_ID} tabIndex={-1} className="flex-1">
        <section className="relative overflow-hidden">
          <div
            aria-hidden="true"
            className={cn(
              "pointer-events-none absolute inset-0",
              "[background:radial-gradient(60%_55%_at_70%_0%,hsl(var(--highlight)_/_0.14),transparent_65%)]",
              "opacity-80 dark:opacity-50"
            )}
          />
          <div
            aria-hidden="true"
            className={cn(
              "pointer-events-none absolute inset-0",
              "[background-image:linear-gradient(to_right,hsl(var(--border)_/_0.35)_1px,transparent_1px),linear-gradient(to_bottom,hsl(var(--border)_/_0.35)_1px,transparent_1px)]",
              "[background-size:64px_64px]",
              "opacity-40 dark:opacity-25"
            )}
          />

          <MarketingContainer
            className={cn(
              "pt-4 pb-12 sm:pt-6 sm:pb-14",
              "lg:min-h-[calc(100svh-4rem)] lg:py-10 lg:flex lg:flex-col"
            )}
          >
            <div className="lg:flex lg:flex-1 lg:items-center">
              <div className="grid w-full gap-12 lg:grid-cols-12 lg:items-center">
                <div className="space-y-6 lg:col-span-6">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="highlight">
                      <SparklesIcon aria-hidden="true" />
                      Travel planning, upgraded
                    </Badge>
                    <span className="text-sm text-muted-foreground">
                      Personalized itineraries, budgets, and logistics.
                    </span>
                  </div>

                  <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl">
                    Plan trips with <span className="text-highlight">clarity</span>, not
                    tabs.
                  </h1>

                  <p className="max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg">
                    TripSage AI turns your preferences and constraints into a day-by-day
                    itinerary you can refine. Add guardrails, swap options, and keep
                    your trip organized from idea to departure.
                  </p>

                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                    <Button asChild size="lg" className="sm:w-auto">
                      <Link href={ROUTES.register}>
                        Start planning
                        <ArrowRightIcon aria-hidden="true" className="size-4" />
                      </Link>
                    </Button>
                    <Button asChild size="lg" variant="outline" className="sm:w-auto">
                      <Link href={ROUTES.aiDemo}>Try the live demo</Link>
                    </Button>
                  </div>

                  <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
                    {QUICK_CHECKS.map((label) => (
                      <span key={label} className="inline-flex items-center gap-2">
                        <CheckIcon
                          aria-hidden="true"
                          className="size-4 text-highlight"
                        />
                        {label}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="lg:col-span-6">
                  <Card className="overflow-hidden shadow-sm">
                    <CardHeader className="gap-3">
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0 space-y-1">
                          <CardTitle className="text-xl">Tokyo • 5 days</CardTitle>
                          <p className="text-sm text-muted-foreground">
                            Balanced pace · Food · Neighborhood hopping
                          </p>
                        </div>
                        <Badge variant="secondary">Draft</Badge>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="ghost">Flights: flexible</Badge>
                        <Badge variant="ghost">Hotel: mid-range</Badge>
                        <Badge variant="ghost">Commute: low</Badge>
                      </div>
                    </CardHeader>

                    <CardContent className="space-y-4 p-6">
                      <div className="space-y-3">
                        <div className="flex items-start gap-3 rounded-lg border bg-background p-3">
                          <div className="mt-0.5 grid size-8 place-items-center rounded-md bg-muted text-highlight">
                            <MapPinIcon aria-hidden="true" className="size-4" />
                          </div>
                          <div className="min-w-0">
                            <p className="font-medium leading-none">
                              Day 1 · Asakusa + Sumida River
                            </p>
                            <p className="mt-1 text-sm text-muted-foreground">
                              Arrive, settle in, Senso‑ji at golden hour, riverside
                              walk.
                            </p>
                          </div>
                        </div>

                        <div className="flex items-start gap-3 rounded-lg border bg-background p-3">
                          <div className="mt-0.5 grid size-8 place-items-center rounded-md bg-muted text-highlight">
                            <SparklesIcon aria-hidden="true" className="size-4" />
                          </div>
                          <div className="min-w-0">
                            <p className="font-medium leading-none">
                              Day 2 · Shibuya + coffee crawl
                            </p>
                            <p className="mt-1 text-sm text-muted-foreground">
                              Scenic neighborhoods, three café stops, and a flexible
                              night plan.
                            </p>
                          </div>
                        </div>

                        <div className="flex items-start gap-3 rounded-lg border bg-background p-3">
                          <div className="mt-0.5 grid size-8 place-items-center rounded-md bg-muted text-highlight">
                            <CompassIcon aria-hidden="true" className="size-4" />
                          </div>
                          <div className="min-w-0">
                            <p className="font-medium leading-none">
                              Day 3 · Day trip options
                            </p>
                            <p className="mt-1 text-sm text-muted-foreground">
                              Nikko or Kamakura with clear tradeoffs for time and cost.
                            </p>
                          </div>
                        </div>
                      </div>

                      <div className="rounded-lg border bg-background p-4">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium">Budget snapshot</p>
                          <p className="text-sm text-muted-foreground">Per person</p>
                        </div>
                        <div className="mt-3 grid gap-2 text-sm tabular-nums">
                          <div className="flex items-center justify-between">
                            <span className="text-muted-foreground">Flights</span>
                            <span className="font-medium">$900–$1,250</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-muted-foreground">Hotel</span>
                            <span className="font-medium">$750–$1,050</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-muted-foreground">
                              Food + transit
                            </span>
                            <span className="font-medium">$280–$420</span>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </div>

            <div className="mt-10 pt-8 lg:mt-0">
              <p className="text-center text-sm text-muted-foreground">
                Powered by modern infrastructure you already trust
              </p>
              <TooltipProvider delayDuration={450}>
                <ul className="mt-5 flex flex-wrap items-center justify-center gap-2">
                  {TRUST_MARKS.map((mark) => (
                    <li key={mark}>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Badge
                            variant="outline"
                            className="bg-background/60 text-muted-foreground"
                          >
                            {mark}
                          </Badge>
                        </TooltipTrigger>
                        <TooltipContent sideOffset={8}>
                          {TRUST_MARK_DESCRIPTIONS[mark]}
                        </TooltipContent>
                      </Tooltip>
                    </li>
                  ))}
                </ul>
              </TooltipProvider>
            </div>
          </MarketingContainer>
        </section>

        <section>
          <div className={cn(MARKETING_CONTAINER_CLASS, "py-14 sm:py-16 lg:py-20")}>
            <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div className="space-y-2">
                <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                  Everything you need to plan faster
                </h2>
                <p className="max-w-2xl text-muted-foreground">
                  TripSage is opinionated about structure, not about your travel style.
                  Keep the plan clean, editable, and easy to share.
                </p>
              </div>
              <Button asChild variant="ghost" className="self-start md:self-auto">
                <Link href={ROUTES.aiDemo}>
                  Explore the demo
                  <ArrowRightIcon aria-hidden="true" className="size-4" />
                </Link>
              </Button>
            </div>

            <div className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-12">
              {FEATURE_CARDS.map(
                ({ description, href, highlights, icon: Icon, title, variant }) => {
                  const spanClass =
                    variant === "bento" ? "lg:col-span-6" : "lg:col-span-3";
                  const isBento = variant === "bento";

                  return (
                    <Link
                      key={title}
                      href={href}
                      className={cn("group block focus:outline-none", spanClass)}
                      aria-label={`${title}: ${description}`}
                    >
                      <Card
                        className={cn(
                          "h-full transition-[background-color,border-color,box-shadow] focus-within:ring-2 focus-within:ring-ring",
                          "hover:bg-muted/40 hover:border-foreground/10 hover:shadow-sm"
                        )}
                      >
                        <CardHeader className={cn("gap-3", isBento ? "p-5" : "p-4")}>
                          <div className="flex items-center justify-between gap-4">
                            <CardTitle className="min-w-0 text-lg">{title}</CardTitle>
                            <div
                              className={cn(
                                "grid shrink-0 place-items-center rounded-lg border bg-background text-highlight shadow-xs",
                                isBento ? "size-10" : "size-9"
                              )}
                            >
                              <Icon
                                aria-hidden="true"
                                className={isBento ? "size-5" : "size-4"}
                              />
                            </div>
                          </div>

                          <p className="text-sm leading-relaxed text-muted-foreground">
                            {description}
                          </p>

                          {variant === "bento" && highlights ? (
                            <ul className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-3">
                              {highlights.slice(0, 3).map((item) => (
                                <li
                                  key={item}
                                  className="inline-flex items-center gap-2"
                                >
                                  <CheckIcon
                                    aria-hidden="true"
                                    className="size-4 text-highlight"
                                  />
                                  <span className="min-w-0 truncate">{item}</span>
                                </li>
                              ))}
                            </ul>
                          ) : null}
                        </CardHeader>
                      </Card>
                    </Link>
                  );
                }
              )}
            </div>
          </div>
        </section>

        <section>
          <div className={cn(MARKETING_CONTAINER_CLASS, "py-14 sm:py-16 lg:py-20")}>
            <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div className="space-y-2">
                <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                  How it works
                </h2>
                <p className="max-w-2xl text-muted-foreground">
                  A simple loop: define constraints, generate a plan, refine until it’s
                  yours.
                </p>
              </div>
            </div>

            <Card className="mt-8 overflow-hidden bg-background/70 supports-[backdrop-filter]:bg-background/55 supports-[backdrop-filter]:backdrop-blur">
              <CardContent className="p-0">
                <ol className="grid gap-0 sm:grid-cols-3">
                  {STEPS.map(({ description, icon: Icon, title }, index) => (
                    <li key={title} className="relative">
                      <div className="flex h-full flex-col gap-3 p-6">
                        <div className="flex items-center justify-between gap-4">
                          <div className="flex items-center gap-3">
                            <div className="flex size-10 items-center justify-center rounded-full border bg-background text-sm font-semibold tabular-nums text-highlight shadow-xs">
                              {index + 1}
                            </div>
                            <CardTitle className="text-base">{title}</CardTitle>
                          </div>
                          <div className="grid size-10 place-items-center rounded-lg border bg-background text-highlight shadow-xs">
                            <Icon aria-hidden="true" className="size-5" />
                          </div>
                        </div>
                        <p className="text-sm leading-relaxed text-muted-foreground">
                          {description}
                        </p>
                      </div>
                    </li>
                  ))}
                </ol>
              </CardContent>
            </Card>
          </div>
        </section>

        <section>
          <div className={cn(MARKETING_CONTAINER_CLASS, "py-14 sm:py-16 lg:py-20")}>
            <div className="grid gap-6 lg:grid-cols-3">
              <div className="space-y-3 lg:col-span-1">
                <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                  Designed for real travel days
                </h2>
                <p className="text-muted-foreground">
                  TripSage focuses on the annoying details, timing, pacing, and
                  tradeoffs, so the plan holds up when you’re actually on the move.
                </p>
                <Button asChild variant="link" className="px-0">
                  <Link href={ROUTES.faq}>Read FAQs</Link>
                </Button>
              </div>

              <div className="grid gap-4 lg:col-span-2 sm:grid-cols-2">
                {TESTIMONIALS.map(({ body, initials, label, name, role }) => (
                  <Card
                    key={name}
                    className={cn(
                      "h-full transition-[background-color,border-color,box-shadow]",
                      "hover:bg-muted/25 hover:border-foreground/10 hover:shadow-sm"
                    )}
                  >
                    <CardHeader className="gap-4 p-5">
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-2">
                          <Badge variant="highlight" className="w-fit">
                            {label}
                          </Badge>
                          <CardTitle className="text-lg leading-snug">
                            “{body.split(".")[0]}.”
                          </CardTitle>
                        </div>
                        <Avatar className="size-10 border bg-background shadow-xs">
                          <AvatarFallback className="text-sm font-semibold text-foreground">
                            {initials}
                          </AvatarFallback>
                        </Avatar>
                      </div>
                    </CardHeader>
                    <CardContent className="px-5 pb-5 pt-0 text-sm leading-relaxed text-muted-foreground">
                      {body}
                      <p className="mt-4 text-xs font-medium text-foreground">
                        {name} · <span className="text-muted-foreground">{role}</span>
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>

            <div className="mt-10 rounded-2xl border bg-background p-8 sm:p-10">
              <div className="grid gap-6 lg:grid-cols-2 lg:items-center">
                <div className="space-y-3">
                  <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                    Ready to plan your next trip?
                  </h2>
                  <p className="text-muted-foreground">
                    Start with a quick draft, then refine until it’s exactly right.
                    Clean output, clear tradeoffs, and no chaos.
                  </p>
                </div>
                <div className="flex flex-col gap-3 sm:flex-row lg:justify-end">
                  <Button asChild size="lg">
                    <Link href={ROUTES.register}>
                      Create your account
                      <ArrowRightIcon aria-hidden="true" className="size-4" />
                    </Link>
                  </Button>
                  <Button asChild size="lg" variant="outline">
                    <Link href={ROUTES.login}>Log in</Link>
                  </Button>
                  <Button asChild size="lg" variant="ghost">
                    <Link href={ROUTES.faq}>FAQs</Link>
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t">
        <MarketingContainer className="flex flex-col items-center justify-between gap-4 py-8 md:h-24 md:flex-row md:py-0">
          <p className="text-center text-sm leading-loose text-muted-foreground md:text-left">
            © <CurrentYear /> TripSage AI. All rights reserved.
          </p>
          <div className="flex items-center gap-4">
            <Link
              href={ROUTES.privacy}
              className="text-sm text-muted-foreground underline-offset-4 hover:underline"
            >
              Privacy
            </Link>
            <Link
              href={ROUTES.faq}
              className="text-sm text-muted-foreground underline-offset-4 hover:underline"
            >
              FAQs
            </Link>
            <Link
              href={ROUTES.terms}
              className="text-sm text-muted-foreground underline-offset-4 hover:underline"
            >
              Terms
            </Link>
            <Link
              href={ROUTES.contact}
              className="text-sm text-muted-foreground underline-offset-4 hover:underline"
            >
              Contact
            </Link>
          </div>
        </MarketingContainer>
      </footer>
    </>
  );
}
