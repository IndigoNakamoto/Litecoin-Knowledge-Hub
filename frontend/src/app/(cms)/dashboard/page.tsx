import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function DashboardPage() {
  // This is a placeholder for now. In a real app, you would fetch and display
  // a list of articles.
  return (
    <div className="container mx-auto p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">CMS Dashboard</h1>
        <Button asChild>
          <Link href="/editor/new">Create New Article</Link>
        </Button>
      </div>
      <div className="border rounded-lg p-4">
        <p>Article list will be displayed here.</p>
      </div>
    </div>
  );
}
