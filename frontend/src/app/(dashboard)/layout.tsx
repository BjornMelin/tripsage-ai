import { DashboardLayout } from "@/components/layouts/dashboard-layout";

// Force dynamic rendering to avoid SSG issues with authentication
export const dynamic = 'force-dynamic';

export default function Layout({ children }: { children: React.ReactNode }) {
  return <DashboardLayout>{children}</DashboardLayout>;
}
