import ArticleEditor from '@/components/cms/ArticleEditor';

// This is a placeholder for now. In a real app, you would fetch the article
// data based on the ID and pass it to the ArticleEditor.
type EditorPageParams = { _id: string }

export default async function EditArticlePage({ params }: { params: Promise<EditorPageParams> }) {
  const resolvedParams = await params
  return (
    <div>
      <h1 className="text-3xl font-bold mb-4">Editing Article: {resolvedParams._id}</h1>
      <ArticleEditor />
    </div>
  );
}
