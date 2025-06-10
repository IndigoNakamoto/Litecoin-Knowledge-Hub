import ArticleEditor from '@/components/cms/ArticleEditor';

// This is a placeholder for now. In a real app, you would fetch the article
// data based on the ID and pass it to the ArticleEditor.
export default function EditArticlePage({ params }: { params: { id: string } }) {
  return (
    <div>
      <h1 className="text-3xl font-bold mb-4">Editing Article: {params.id}</h1>
      <ArticleEditor />
    </div>
  );
}
