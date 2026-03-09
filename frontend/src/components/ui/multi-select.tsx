'use client';

import * as React from 'react';
import { X, Check, ChevronDown, Plus, Search } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export interface MultiSelectOption {
  value: string;
  label: string;
}

interface MultiSelectProps {
  selected: string[];
  options: MultiSelectOption[];
  onChange: (value: string[]) => void;
  placeholder?: string;
  className?: string;
}

export function MultiSelect({
  selected,
  options,
  onChange,
  placeholder = "Select options...",
  className,
}: MultiSelectProps) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');
  const [activeIndex, setActiveIndex] = React.useState(0);
  const containerRef = React.useRef<HTMLDivElement>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const id = React.useId();
  const optionsId = `multi-select-options-${id}`;

  const available = options.filter(
    (o) => !selected.includes(o.value) && 
    (o.label.toLowerCase().includes(search.toLowerCase()) || 
     o.value.toLowerCase().includes(search.toLowerCase()))
  );

  const toggleOpen = () => {
    const nextOpen = !open;
    setOpen(nextOpen);
    if (nextOpen) {
        setSearch('');
        setActiveIndex(0);
        // Focus input if searchable
        setTimeout(() => inputRef.current?.focus(), 0);
    }
  };

  const handleSelect = (value: string) => {
    onChange([...selected, value]);
    setSearch('');
    setOpen(false);
  };

  const handleRemove = (value: string) => {
    onChange(selected.filter((v) => v !== value));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (!open) {
        toggleOpen();
      } else {
        setActiveIndex((prev) => (prev + 1) % Math.max(available.length, 1));
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (open) {
        setActiveIndex((prev) => (prev - 1 + available.length) % Math.max(available.length, 1));
      }
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (open && available[activeIndex]) {
        handleSelect(available[activeIndex].value);
      } else if (!open) {
        toggleOpen();
      }
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  // Close on outside click
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className={cn("space-y-2", className)} ref={containerRef}>
      <div className="flex flex-wrap gap-1.5 min-h-[1.5rem]">
        {selected.map((value) => {
          const option = options.find((o) => o.value === value);
          const displayLabel = option?.label ?? value;
          return (
            <Badge key={value} variant="secondary" className="px-2 py-0.5 gap-1.5 flex items-center group">
              <span className="text-xs">{displayLabel}</span>
              <button
                type="button"
                aria-label={`Remove ${displayLabel}`}
                onClick={() => handleRemove(value)}
                className="hover:text-red-500 rounded-full focus:outline-none focus:ring-1 focus:ring-red-500"
              >
                <X className="w-3 h-3" />
              </button>
            </Badge>
          );
        })}
        {selected.length === 0 && !open && (
            <span className="text-xs text-muted-foreground italic">{placeholder}</span>
        )}
      </div>

      <div className="relative">
        <div className="flex items-center gap-2">
            <Button
                type="button"
                variant="outline"
                size="sm"
                className="text-xs h-8 gap-1.5 pl-2 pr-2"
                onClick={toggleOpen}
                onKeyDown={handleKeyDown}
                aria-haspopup="listbox"
                aria-expanded={open}
                aria-controls={open ? optionsId : undefined}
            >
                {open ? <ChevronDown className="w-3 h-3" /> : <Plus className="w-3 h-3" />}
                <span>{open ? 'Close' : 'Add Option'}</span>
            </Button>
            
            {open && (
                <div className="relative flex-1 max-w-[200px]">
                    <Search className="absolute left-2 top-1.5 h-3.5 w-3.5 text-muted-foreground" />
                    <input
                        ref={inputRef}
                        type="text"
                        role="combobox"
                        aria-autocomplete="list"
                        aria-expanded={open}
                        aria-haspopup="listbox"
                        aria-controls={optionsId}
                        className="w-full h-8 pl-8 pr-2 text-xs border rounded-md focus:outline-none focus:ring-1 focus:ring-primary bg-background"
                        placeholder="Search..."
                        value={search}
                        onChange={(e) => {
                            setSearch(e.target.value);
                            setActiveIndex(0);
                        }}
                        onKeyDown={handleKeyDown}
                        autoComplete="off"
                    />
                </div>
            )}
        </div>

        {open && available.length > 0 && (
          <div 
            id={optionsId}
            role="listbox"
            className="absolute z-50 mt-1 w-full min-w-[250px] bg-popover text-popover-foreground border rounded-md shadow-lg max-h-48 overflow-y-auto"
          >
            {available.map((option, index) => (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={index === activeIndex}
                className={cn(
                  "w-full text-left px-3 py-2 text-xs transition-colors flex items-center justify-between",
                  index === activeIndex ? "bg-accent text-accent-foreground" : "hover:bg-muted"
                )}
                onClick={() => handleSelect(option.value)}
                onMouseEnter={() => setActiveIndex(index)}
              >
                <span>{option.label}</span>
                {index === activeIndex && <Check className="w-3 h-3" />}
              </button>
            ))}
          </div>
        )}
        
        {open && available.length === 0 && (
            <div className="absolute z-50 mt-1 w-full bg-popover text-popover-foreground border rounded-md shadow-lg p-3 text-xs text-muted-foreground">
                No options found.
            </div>
        )}
      </div>
    </div>
  );
}
