'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

interface Category {
  id: string
  name: string
  description?: string
  icon?: string
  audienceLevel?: string
  parent?: string
  order: number
}

interface CategoryGroup {
  mainCategory: Category
  subCategories: Category[]
}

const CategoryListView: React.FC = () => {
  const [categoryGroups, setCategoryGroups] = useState<CategoryGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())
  const router = useRouter()

  useEffect(() => {
    fetchCategories()
  }, [])

  const fetchCategories = async () => {
    try {
      const response = await fetch('/api/categories?limit=100&sort=order')
      if (response.ok) {
        const data = await response.json()
        const categories: Category[] = data.docs || []

        // Group categories by parent-child relationship
        const mainCategories = categories.filter(cat => !cat.parent)
        const groups: CategoryGroup[] = mainCategories.map(mainCat => ({
          mainCategory: mainCat,
          subCategories: categories.filter(cat => cat.parent === mainCat.id).sort((a, b) => a.order - b.order)
        }))

        setCategoryGroups(groups)

        // Auto-expand all sections for better visibility
        setExpandedSections(new Set(groups.map(g => g.mainCategory.id)))
      }
    } catch (error) {
      console.error('Failed to fetch categories:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleSection = (mainCategoryId: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(mainCategoryId)) {
      newExpanded.delete(mainCategoryId)
    } else {
      newExpanded.add(mainCategoryId)
    }
    setExpandedSections(newExpanded)
  }

  const handleCreateMainCategory = () => {
    router.push('/admin/collections/categories/create')
  }

  const handleCreateSubcategory = (parentId: string) => {
    // Navigate to create page with parent pre-selected
    router.push(`/admin/collections/categories/create?parent=${parentId}`)
  }

  const handleEditCategory = (categoryId: string) => {
    router.push(`/admin/collections/categories/${categoryId}`)
  }

  if (loading) {
    return <div style={{ padding: '20px' }}>Loading categories...</div>
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '24px',
        paddingBottom: '16px',
        borderBottom: '1px solid var(--theme-border-color)'
      }}>
        <div>
          <h1 style={{
            margin: '0 0 8px 0',
            fontSize: '24px',
            fontWeight: '600',
            color: 'var(--theme-text)'
          }}>
            Category Management
          </h1>
          <p style={{
            margin: '0',
            color: 'var(--theme-text-muted)',
            fontSize: '14px'
          }}>
            Organize your content categories hierarchically. Main categories appear first, followed by their subcategories.
          </p>
        </div>
        <button
          onClick={handleCreateMainCategory}
          style={{
            backgroundColor: 'var(--theme-success-500)',
            color: 'white',
            border: 'none',
            padding: '10px 16px',
            borderRadius: '6px',
            fontSize: '14px',
            fontWeight: '500',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <span>+</span>
          Add Main Category
        </button>
      </div>

      {categoryGroups.length === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '60px 20px',
          backgroundColor: 'var(--theme-elevation-50)',
          borderRadius: '8px',
          border: '2px dashed var(--theme-border-color)'
        }}>
          <h3 style={{ margin: '0 0 16px 0', color: 'var(--theme-text)' }}>
            No categories yet
          </h3>
          <p style={{ margin: '0 0 24px 0', color: 'var(--theme-text-muted)' }}>
            Get started by creating your first main category.
          </p>
          <button
            onClick={handleCreateMainCategory}
            style={{
              backgroundColor: 'var(--theme-primary-500)',
              color: 'white',
              border: 'none',
              padding: '12px 24px',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: '500',
              cursor: 'pointer'
            }}
          >
            Create First Category
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {categoryGroups.map((group) => {
            const { mainCategory, subCategories } = group
            const isExpanded = expandedSections.has(mainCategory.id)

            return (
              <div key={mainCategory.id} style={{
                border: '1px solid var(--theme-border-color)',
                borderRadius: '8px',
                backgroundColor: 'var(--theme-bg)',
                overflow: 'hidden'
              }}>
                {/* Main Category Header */}
                <div style={{
                  backgroundColor: 'var(--theme-elevation-100)',
                  borderBottom: '1px solid var(--theme-border-color)',
                  padding: '16px 20px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <button
                      onClick={() => toggleSection(mainCategory.id)}
                      style={{
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        padding: '4px',
                        borderRadius: '4px',
                        color: 'var(--theme-text-muted)',
                        fontSize: '16px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: '24px',
                        height: '24px'
                      }}
                    >
                      {isExpanded ? '▼' : '▶'}
                    </button>

                    {mainCategory.icon && (
                      <span style={{ fontSize: '24px' }}>{mainCategory.icon}</span>
                    )}

                    <div style={{ flex: 1 }}>
                      <h3 style={{
                        margin: '0 0 4px 0',
                        fontSize: '18px',
                        fontWeight: '600',
                        color: 'var(--theme-text)'
                      }}>
                        {mainCategory.name}
                      </h3>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        {mainCategory.audienceLevel && (
                          <span style={{
                            fontSize: '11px',
                            padding: '3px 8px',
                            borderRadius: '12px',
                            fontWeight: '600',
                            textTransform: 'uppercase',
                            letterSpacing: '0.5px',
                            backgroundColor:
                              mainCategory.audienceLevel === 'beginner' ? 'var(--theme-success-100)' :
                              mainCategory.audienceLevel === 'intermediate' ? 'var(--theme-warning-100)' : 'var(--theme-error-100)',
                            color:
                              mainCategory.audienceLevel === 'beginner' ? 'var(--theme-success-700)' :
                              mainCategory.audienceLevel === 'intermediate' ? 'var(--theme-warning-700)' : 'var(--theme-error-700)'
                          }}>
                            {mainCategory.audienceLevel}
                          </span>
                        )}
                        <span style={{
                          fontSize: '13px',
                          color: 'var(--theme-text-muted)'
                        }}>
                          {subCategories.length} subcategories
                        </span>
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        onClick={() => handleCreateSubcategory(mainCategory.id)}
                        style={{
                          backgroundColor: 'var(--theme-primary-500)',
                          color: 'white',
                          border: 'none',
                          padding: '6px 12px',
                          borderRadius: '4px',
                          fontSize: '12px',
                          fontWeight: '500',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}
                      >
                        <span>+</span>
                        Add Subcategory
                      </button>
                      <button
                        onClick={() => handleEditCategory(mainCategory.id)}
                        style={{
                          backgroundColor: 'var(--theme-elevation-200)',
                          color: 'var(--theme-text)',
                          border: '1px solid var(--theme-border-color)',
                          padding: '6px 12px',
                          borderRadius: '4px',
                          fontSize: '12px',
                          fontWeight: '500',
                          cursor: 'pointer'
                        }}
                      >
                        Edit
                      </button>
                    </div>
                  </div>

                  {mainCategory.description && (
                    <p style={{
                      margin: '8px 0 0 48px',
                      fontSize: '14px',
                      color: 'var(--theme-text-muted)',
                      lineHeight: '1.4'
                    }}>
                      {mainCategory.description}
                    </p>
                  )}
                </div>

                {/* Expandable Subcategories */}
                {isExpanded && (
                  <div style={{ backgroundColor: 'var(--theme-elevation-25)' }}>
                    {subCategories.length === 0 ? (
                      <div style={{
                        padding: '20px',
                        textAlign: 'center',
                        color: 'var(--theme-text-muted)',
                        fontStyle: 'italic'
                      }}>
                        No subcategories yet. Click &quot;Add Subcategory&quot; to create one.
                      </div>
                    ) : (
                      subCategories.map((subCategory) => (
                        <div key={subCategory.id} style={{
                          borderTop: '1px solid var(--theme-border-color)',
                          padding: '12px 20px 12px 68px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px'
                        }}>
                          <div style={{
                            width: '4px',
                            height: '4px',
                            borderRadius: '50%',
                            backgroundColor: 'var(--theme-border-color)',
                            flexShrink: 0
                          }} />

                          <div style={{ flex: 1 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '2px' }}>
                              <span style={{
                                fontWeight: '500',
                                fontSize: '14px',
                                color: 'var(--theme-text)'
                              }}>
                                {subCategory.name}
                              </span>
                              {subCategory.audienceLevel && (
                                <span style={{
                                  fontSize: '10px',
                                  padding: '2px 6px',
                                  borderRadius: '8px',
                                  fontWeight: '600',
                                  textTransform: 'uppercase',
                                  letterSpacing: '0.5px',
                                  backgroundColor:
                                    subCategory.audienceLevel === 'beginner' ? 'var(--theme-success-100)' :
                                    subCategory.audienceLevel === 'intermediate' ? 'var(--theme-warning-100)' : 'var(--theme-error-100)',
                                  color:
                                    subCategory.audienceLevel === 'beginner' ? 'var(--theme-success-700)' :
                                    subCategory.audienceLevel === 'intermediate' ? 'var(--theme-warning-700)' : 'var(--theme-error-700)'
                                }}>
                                  {subCategory.audienceLevel}
                                </span>
                              )}
                            </div>
                            {subCategory.description && (
                              <p style={{
                                margin: '0',
                                fontSize: '13px',
                                color: 'var(--theme-text-muted)',
                                lineHeight: '1.3'
                              }}>
                                {subCategory.description}
                              </p>
                            )}
                          </div>

                          <button
                            onClick={() => handleEditCategory(subCategory.id)}
                            style={{
                              backgroundColor: 'transparent',
                              color: 'var(--theme-text-muted)',
                              border: '1px solid var(--theme-border-color)',
                              padding: '4px 8px',
                              borderRadius: '4px',
                              fontSize: '11px',
                              fontWeight: '500',
                              cursor: 'pointer'
                            }}
                          >
                            Edit
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default CategoryListView
