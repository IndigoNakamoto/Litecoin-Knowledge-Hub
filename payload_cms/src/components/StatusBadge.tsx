import React, { CSSProperties } from 'react';

interface StatusBadgeProps {
  rowData: {
    status?: 'draft' | 'published';
  };
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ rowData }) => {
  const status = rowData?.status || 'draft';
  const style: CSSProperties = {
    display: 'inline-block',
    padding: '0.25em 0.6em',
    fontSize: '75%',
    fontWeight: 700,
    lineHeight: '1',
    textAlign: 'center',
    whiteSpace: 'nowrap',
    verticalAlign: 'baseline',
    borderRadius: '0.375rem',
    color: '#fff',
    backgroundColor: status === 'published' ? '#28a745' : '#ffc107',
  };

  return (
    <span style={style}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
};

export default StatusBadge;
