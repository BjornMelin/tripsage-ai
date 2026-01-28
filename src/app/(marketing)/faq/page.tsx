/**
 * @fileoverview Marketing FAQ page.
 */

import type { Metadata } from "next";
import Link from "next/link";
import { MarketingContainer } from "@/components/marketing/marketing-container";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MAIN_CONTENT_ID } from "@/lib/a11y/landmarks";
import { ROUTES } from "@/lib/routes";
import { cn } from "@/lib/utils";

/** Metadata for the marketing FAQ page. */
export const metadata: Metadata = {
  description:
    "Answers to common questions about TripSage AI: how planning works, budgets, editing, sharing, and more.",
  title: "FAQs",
};

const FAQS = [
  {
    answer:
      "You get a structured draft with day-by-day flow, assumptions, and editable options. You can iterate to tighten pacing, swap activities, and keep the plan coherent.",
    question: "What do I get when I generate a plan?",
    value: "plan",
  },
  {
    answer:
      "TripSage helps you set a budget range and see tradeoffs as you adjust pace, lodging, and activities. You can keep multiple options without losing structure.",
    question: "How do budgets work?",
    value: "budget",
  },
  {
    answer:
      "Yes. The output is meant to be shared and adjusted. You can refine it over time and keep the latest version handy while you travel.",
    question: "Can I share the itinerary and keep editing it?",
    value: "share",
  },
  {
    answer:
      "Not at all. It’s designed for faster planning and clearer decisions, whether you want a lightweight weekend plan or a detailed itinerary with guardrails.",
    question: "Is this only for complex trips?",
    value: "complexity",
  },
  {
    answer:
      "You can start with broad preferences (pace, neighborhoods, must-dos) and then add constraints (budget, commute tolerance, timing). The plan stays structured as you refine.",
    question: "How specific do my inputs need to be?",
    value: "inputs",
  },
  {
    answer:
      "TripSage is built to be transparent: clear assumptions, editable output, and tradeoffs you can understand. When something is uncertain, the UI should make that visible.",
    question: "How do you keep recommendations trustworthy?",
    value: "trust",
  },
] as const;

/** Renders the marketing FAQ page content. */
export default function FaqPage() {
  return (
    <main id={MAIN_CONTENT_ID} tabIndex={-1} className="flex-1">
      <section className="relative">
        <MarketingContainer
          className={cn(
            "pt-6 pb-8 sm:pt-8 sm:pb-10",
            "lg:min-h-[calc(100svh-4rem-1px)] lg:py-8 lg:flex lg:flex-col"
          )}
        >
          <div className="lg:flex lg:flex-1 lg:items-center">
            <div className="grid w-full gap-6 lg:grid-cols-2 lg:items-start">
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="highlight">Help center</Badge>
                  <span className="text-sm text-muted-foreground">FAQs</span>
                </div>
                <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                  Fast answers, fewer tabs.
                </h1>
                <p className="max-w-xl text-base leading-relaxed text-muted-foreground">
                  The goal is simple: keep planning clear. If you don’t see what you
                  need, reach out and we’ll help.
                </p>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                  <Button asChild size="lg" className="sm:w-auto">
                    <Link href={ROUTES.register}>Start planning</Link>
                  </Button>
                  <Button asChild variant="outline" size="lg" className="sm:w-auto">
                    <Link href={ROUTES.contact}>Contact</Link>
                  </Button>
                </div>
              </div>

              <Card className="shadow-sm">
                <CardHeader className="p-5">
                  <CardTitle className="text-lg">Frequently asked</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <Accordion
                    type="single"
                    collapsible
                    className="w-full divide-y divide-border/40"
                  >
                    {FAQS.map(({ answer, question, value }) => (
                      <AccordionItem key={value} value={value} className="border-b-0">
                        <AccordionTrigger className="px-5 py-3 text-left hover:no-underline hover:bg-muted/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background">
                          {question}
                        </AccordionTrigger>
                        <AccordionContent className="px-5 pb-3 text-sm leading-relaxed text-muted-foreground">
                          {answer}
                        </AccordionContent>
                      </AccordionItem>
                    ))}
                  </Accordion>
                </CardContent>
              </Card>
            </div>
          </div>
        </MarketingContainer>
      </section>
    </main>
  );
}
