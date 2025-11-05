import React from 'react'

interface CategoryCellProps {
  cellData: string
  rowData: {
    name?: string
    parent?: any
    icon?: string
    order?: number
  }
}

const CategoryCell: React.FC<CategoryCellProps> = ({ cellData, rowData }) => {
  const { parent, icon, order } = rowData
  const name = cellData || rowData.name

  // If this is a parent category (no parent), show with icon
  if (!parent) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {icon && <span>{icon}</span>}
        <strong>{name}</strong>
        <span style={{ color: '#666', fontSize: '12px' }}>
          (Order: {order || 0})
        </span>
      </div>
    )
  }

  // If this is a child category, show with indentation
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      marginLeft: '20px',
      paddingLeft: '12px',
      borderLeft: '2px solid #e0e0e0'
    }}>
      <span>{name}</span>
      <span style={{ color: '#666', fontSize: '12px' }}>
        (Order: {order || 0})
      </span>
    </div>
  )
}

export default CategoryCell
