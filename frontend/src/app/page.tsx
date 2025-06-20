import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Image from "next/image";
import Link from "next/link";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 flex h-16 items-center gap-4 border-b bg-background px-6">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          TripSage AI
        </Link>
        <div className="ml-auto flex items-center gap-4">
          <Link href="/auth/login">
            <Button variant="outline">Log in</Button>
          </Link>
          <Link href="/auth/register">
            <Button>Sign up</Button>
          </Link>
        </div>
      </header>
      <main className="flex-1">
        <section className="px-4 py-12 md:py-24 lg:py-32">
          <div className="container mx-auto grid gap-6 lg:grid-cols-2 lg:gap-12 items-center">
            <div className="space-y-4">
              <h1 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl">
                Plan Your Perfect Trip with TripSage AI
              </h1>
              <p className="text-muted-foreground md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed">
                Intelligent travel planning powered by AI. Get personalized
                recommendations, budget optimization, and seamless booking - all in one
                place.
              </p>
              <div className="flex flex-col gap-2 min-[400px]:flex-row">
                <Link href="/auth/register">
                  <Button size="lg" className="w-full min-[400px]:w-auto">
                    Get Started
                  </Button>
                </Link>
                <Link href="/dashboard/chat">
                  <Button
                    size="lg"
                    variant="outline"
                    className="w-full min-[400px]:w-auto"
                  >
                    Try Demo
                  </Button>
                </Link>
              </div>
            </div>
            <div className="mx-auto max-w-md">
              <Image
                src="/next.svg"
                alt="TripSage AI"
                width={420}
                height={420}
                className="dark:invert"
                style={{ width: "100%", height: "auto" }}
                priority
              />
            </div>
          </div>
        </section>
        <section className="bg-muted py-12 md:py-24 lg:py-32">
          <div className="container mx-auto space-y-12 px-4 md:px-6">
            <div className="flex flex-col items-center justify-center space-y-4 text-center">
              <div className="space-y-2">
                <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl">
                  Why Choose TripSage AI?
                </h2>
                <p className="mx-auto max-w-[700px] text-muted-foreground md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed">
                  Our AI-powered platform makes travel planning simpler, smarter, and
                  more personalized than ever before.
                </p>
              </div>
            </div>
            <div className="mx-auto grid max-w-5xl gap-6 md:grid-cols-2 lg:grid-cols-3">
              <Card>
                <CardHeader>
                  <CardTitle>AI-Powered Planning</CardTitle>
                </CardHeader>
                <CardContent>
                  <p>
                    Get intelligent recommendations based on your preferences, budget,
                    and travel style.
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Budget Optimization</CardTitle>
                </CardHeader>
                <CardContent>
                  <p>
                    Find the best deals and optimize your spending across flights,
                    hotels, and activities.
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>All-in-One Platform</CardTitle>
                </CardHeader>
                <CardContent>
                  <p>
                    Plan, book, and manage your entire trip in one seamless experience.
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </section>
      </main>
      <footer className="border-t py-6 md:py-0">
        <div className="container flex flex-col items-center justify-between gap-4 md:h-24 md:flex-row">
          <p className="text-center text-sm leading-loose text-muted-foreground md:text-left">
            © {new Date().getFullYear()} TripSage AI. All rights reserved.
          </p>
          <div className="flex items-center gap-4">
            <Link
              href="/privacy"
              className="text-sm text-muted-foreground underline-offset-4 hover:underline"
            >
              Privacy
            </Link>
            <Link
              href="/terms"
              className="text-sm text-muted-foreground underline-offset-4 hover:underline"
            >
              Terms
            </Link>
            <Link
              href="/contact"
              className="text-sm text-muted-foreground underline-offset-4 hover:underline"
            >
              Contact
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
