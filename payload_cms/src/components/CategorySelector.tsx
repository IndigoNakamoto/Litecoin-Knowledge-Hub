'use client'

import React, { useState, useEffect } from 'react'
import { useField } from '@payloadcms/ui'

interface Category {
  id: string
  name: string
  description?: string
  icon?: string
  audienceLevel?: string
  parent?: string | { id: string } | null
  order: number
}

interface CategoryGroup {
  mainCategory: Category
  subCategories: Category[]
}

const CategorySelector: React.FC<any> = (props) => {
  const { value, setValue } = useField(props)
  const [categoryGroups, setCategoryGroups] = useState<CategoryGroup[]>([])
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)

  useEffect(() => {
  const fetchCategories = async () => {
    try {
      const response = await fetch('/api/categories?limit=100&sort=order&depth=1')
      if (response.ok) {
        const data = await response.json()
        const categories: Category[] = data.docs || []

        console.log('Fetched categories:', categories) // Debug log

        // Group categories by parent-child relationship
        const mainCategories = categories.filter(cat => {
          // Check if category has no parent (null, undefined, or empty string)
          return !cat.parent || cat.parent === '' || (typeof cat.parent === 'object' && !cat.parent?.id)
        })

        const groups: CategoryGroup[] = mainCategories.map(mainCat => ({
          mainCategory: mainCat,
          subCategories: categories.filter(cat => {
            // Handle different parent field formats
            let parentId = null
            if (typeof cat.parent === 'string') {
              parentId = cat.parent
            } else if (typeof cat.parent === 'object' && cat.parent !== null) {
              parentId = cat.parent.id
            }
            return parentId === mainCat.id
          }).sort((a, b) => a.order - b.order)
        }))

        console.log('Category groups:', groups) // Debug log

        setCategoryGroups(groups)

        // Auto-expand sections that have selected subcategories
        const shouldExpand = new Set<string>()
        groups.forEach(group => {
          if (group.subCategories.some(sub => isCategorySelected(sub.id))) {
            shouldExpand.add(group.mainCategory.id)
          }
        })
        setExpandedSections(shouldExpand)
      }
    } catch (error) {
      console.error('Failed to fetch categories:', error)
    } finally {
      setLoading(false)
    }
  }

    fetchCategories()
  }, [])

  const handleCategoryToggle = (categoryId: string) => {
    // Extract current IDs from the value (handles both string arrays and object arrays)
    const currentIds = Array.isArray(value) ? value.map((item: any) =>
      typeof item === 'string' ? item : item?.id
    ).filter(Boolean) : []

    const isSelected = currentIds.includes(categoryId)

    let newIds
    if (isSelected) {
      newIds = currentIds.filter(id => id !== categoryId)
    } else {
      newIds = [...currentIds, categoryId]
    }

    // Convert back to the format Payload expects
    // Check what format the current value uses
    const currentFormat = Array.isArray(value) && value.length > 0 ? typeof value[0] : 'string'
    const newValue = currentFormat === 'object' ?
      newIds.map(id => ({id})) : newIds

    setValue(newValue)
  }

  const handleMainCategoryToggle = (mainCategoryId: string, subCategoryIds: string[]) => {
    // Extract current IDs from the value (handles both string arrays and object arrays)
    const currentIds = Array.isArray(value) ? value.map((item: any) =>
      typeof item === 'string' ? item : item?.id
    ).filter(Boolean) : []

    const isMainSelected = currentIds.includes(mainCategoryId)
    const selectedSubCategories = subCategoryIds.filter(id => currentIds.includes(id))

    let newIds
    if (isMainSelected) {
      // If main category is selected, deselect it and all subcategories
      newIds = currentIds.filter(id => id !== mainCategoryId && !subCategoryIds.includes(id))
    } else {
      // If main category is not selected, select it and all subcategories
      newIds = [...currentIds, mainCategoryId, ...subCategoryIds.filter(id => !currentIds.includes(id))]
    }

    // Convert back to the format Payload expects
    // Check what format the current value uses
    const currentFormat = Array.isArray(value) && value.length > 0 ? typeof value[0] : 'string'
    const newValue = currentFormat === 'object' ?
      newIds.map(id => ({id})) : newIds

    setValue(newValue)
  }

  const isCategorySelected = (categoryId: string) => {
    // Handle both array of IDs and array of objects
    if (!Array.isArray(value)) return false

    return value.some((item: any) => {
      if (typeof item === 'string') return item === categoryId
      if (typeof item === 'object' && item?.id) return item.id === categoryId
      return false
    })
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

  const getSelectedCount = (categories: Category[]) => {
    return categories.filter(cat => isCategorySelected(cat.id)).length
  }

  if (loading) {
    return <div style={{ padding: '16px', color: 'var(--theme-text)' }}>Loading categories...</div>
  }

  return (
    <div style={{
      maxHeight: '500px',
      overflowY: 'auto',
      border: '1px solid var(--theme-border-color)',
      borderRadius: '6px',
      backgroundColor: 'var(--theme-bg)',
      color: 'var(--theme-text)'
    }}>
      <div style={{
        padding: '16px 16px 12px 16px',
        borderBottom: '1px solid var(--theme-border-color)',
        backgroundColor: 'var(--theme-elevation-50)'
      }}>
        <h4 style={{
          margin: '0 0 8px 0',
          fontSize: '16px',
          fontWeight: '600',
          color: 'var(--theme-text)'
        }}>
          Select Categories
        </h4>
        <p style={{
          margin: '0',
          fontSize: '14px',
          color: 'var(--theme-text-muted)',
          lineHeight: '1.4'
        }}>
          Choose categories that best describe your article content. Expand sections to see subcategories.
        </p>
      </div>

      <div style={{ padding: '8px' }}>
        {categoryGroups.map((group) => {
          const { mainCategory, subCategories } = group
          const isExpanded = expandedSections.has(mainCategory.id)
          const selectedCount = getSelectedCount([mainCategory, ...subCategories])

          return (
            <div key={mainCategory.id} style={{ marginBottom: '8px' }}>
              {/* Main Category Header */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '12px 16px',
                  border: '1px solid var(--theme-border-color)',
                  borderRadius: '6px',
                  backgroundColor: selectedCount > 0 ? 'var(--theme-success-50)' : 'var(--theme-elevation-50)',
                  transition: 'all 0.15s ease',
                  fontWeight: '600'
                }}
              >
                <input
                  type="checkbox"
                  id={`maincategory-${mainCategory.id}`}
                  checked={isCategorySelected(mainCategory.id)}
                  onChange={(e) => {
                    e.stopPropagation()
                    handleMainCategoryToggle(mainCategory.id, subCategories.map(sub => sub.id))
                  }}
                  style={{
                    marginTop: '2px',
                    flexShrink: 0,
                    accentColor: 'var(--theme-success-500)',
                    cursor: 'pointer'
                  }}
                />

                <span
                  onClick={() => toggleSection(mainCategory.id)}
                  style={{
                    fontSize: '16px',
                    transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                    transition: 'transform 0.15s ease',
                    color: 'var(--theme-text-muted)',
                    cursor: 'pointer'
                  }}
                >
                  ▶
                </span>

                {mainCategory.icon && (
                  <span style={{ fontSize: '20px', lineHeight: '1' }}>{mainCategory.icon}</span>
                )}

                <label
                  htmlFor={`maincategory-${mainCategory.id}`}
                  onClick={() => toggleSection(mainCategory.id)}
                  style={{
                    flex: 1,
                    fontSize: '15px',
                    color: 'var(--theme-text)',
                    fontWeight: '600',
                    cursor: 'pointer',
                    margin: 0
                  }}
                >
                  {mainCategory.name}
                </label>

                {selectedCount > 0 && (
                  <span style={{
                    fontSize: '12px',
                    padding: '4px 8px',
                    borderRadius: '12px',
                    backgroundColor: 'var(--theme-success-500)',
                    color: 'white',
                    fontWeight: '600'
                  }}>
                    {selectedCount} selected
                  </span>
                )}

                <span style={{
                  fontSize: '12px',
                  color: 'var(--theme-text-muted)',
                  fontWeight: 'normal'
                }}>
                  {subCategories.length} subcategories
                </span>
              </div>

              {/* Expandable Subcategories */}
              {isExpanded && subCategories.length > 0 && (
                <div style={{
                  marginTop: '4px',
                  marginLeft: '20px',
                  paddingLeft: '16px',
                  borderLeft: '2px solid var(--theme-border-color)',
                  backgroundColor: 'var(--theme-elevation-25)'
                }}>
                  {subCategories.map((subCategory) => (
                    <div
                      key={subCategory.id}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '12px',
                        padding: '8px 12px',
                        marginBottom: '4px',
                        border: `1px solid ${isCategorySelected(subCategory.id) ? 'var(--theme-success-400)' : 'transparent'}`,
                        borderRadius: '4px',
                        backgroundColor: isCategorySelected(subCategory.id) ? 'var(--theme-success-25)' : 'transparent',
                        transition: 'all 0.15s ease'
                      }}
                      title={subCategory.description || 'No description available'}
                    >
                      <input
                        type="checkbox"
                        id={`subcategory-${subCategory.id}`}
                        checked={isCategorySelected(subCategory.id)}
                        onChange={(e) => {
                          e.stopPropagation()
                          handleCategoryToggle(subCategory.id)
                        }}
                        style={{
                          marginTop: '2px',
                          flexShrink: 0,
                          accentColor: 'var(--theme-success-500)',
                          cursor: 'pointer'
                        }}
                      />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <label
                          htmlFor={`subcategory-${subCategory.id}`}
                          style={{
                            cursor: 'pointer',
                            display: 'block',
                            margin: 0,
                            padding: 0
                          }}
                        >
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            marginBottom: '4px',
                            flexWrap: 'wrap'
                          }}>
                            <span style={{
                              fontWeight: '500',
                              fontSize: '13px',
                              color: 'var(--theme-text)',
                              lineHeight: '1.2'
                            }}>
                              {subCategory.name}
                            </span>
                            {subCategory.audienceLevel && (
                              <span style={{
                                fontSize: '9px',
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
                                  subCategory.audienceLevel === 'intermediate' ? 'var(--theme-warning-700)' : 'var(--theme-error-700)',
                                border: `1px solid ${
                                  subCategory.audienceLevel === 'beginner' ? 'var(--theme-success-200)' :
                                  subCategory.audienceLevel === 'intermediate' ? 'var(--theme-warning-200)' : 'var(--theme-error-200)'
                                }`
                              }}>
                                {subCategory.audienceLevel}
                              </span>
                            )}
                          </div>
                          {subCategory.description && (
                            <div style={{
                              fontSize: '12px',
                              color: 'var(--theme-text-muted)',
                              lineHeight: '1.3',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical'
                            }}>
                              {subCategory.description}
                            </div>
                          )}
                        </label>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}

        {categoryGroups.length === 0 && (
          <div style={{
            padding: '24px',
            textAlign: 'center',
            color: 'var(--theme-text-muted)',
            fontStyle: 'italic',
            backgroundColor: 'var(--theme-elevation-50)',
            borderRadius: '6px'
          }}>
            No categories available. Please create categories first in the Categories section.
          </div>
        )}
      </div>
    </div>
  )
}

export default CategorySelector
