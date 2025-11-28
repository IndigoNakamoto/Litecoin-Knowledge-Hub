import * as React from "react"
import { ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

interface AccordionContextValue {
  value?: string
  onValueChange?: (value: string | undefined) => void
}

interface AccordionItemContextValue {
  value: string
}

const AccordionContext = React.createContext<AccordionContextValue>({})
const AccordionItemContext = React.createContext<AccordionItemContextValue | null>(null)

interface AccordionProps extends React.HTMLAttributes<HTMLDivElement> {
  type?: "single"
  collapsible?: boolean
  value?: string
  defaultValue?: string
  onValueChange?: (value: string | undefined) => void
}

const Accordion = React.forwardRef<HTMLDivElement, AccordionProps>(
  ({ type = "single", collapsible = false, value: controlledValue, defaultValue, onValueChange, className, children, ...props }, ref) => {
    const [internalValue, setInternalValue] = React.useState<string | undefined>(defaultValue)
    const value = controlledValue !== undefined ? controlledValue : internalValue
    
    const handleValueChange = React.useCallback((newValue: string | undefined) => {
      if (controlledValue === undefined) {
        setInternalValue(newValue)
      }
      onValueChange?.(newValue)
    }, [controlledValue, onValueChange])

    const contextValue = React.useMemo(() => ({
      value,
      onValueChange: (itemValue: string | undefined) => {
        if (type === "single" && itemValue !== undefined) {
          const newValue = value === itemValue && collapsible ? undefined : itemValue
          handleValueChange(newValue)
        }
      }
    }), [value, type, collapsible, handleValueChange])

    return (
      <AccordionContext.Provider value={contextValue}>
        <div ref={ref} className={cn("space-y-0", className)} {...props}>
          {children}
        </div>
      </AccordionContext.Provider>
    )
  }
)
Accordion.displayName = "Accordion"

interface AccordionItemProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string
}

const AccordionItem = React.forwardRef<HTMLDivElement, AccordionItemProps>(
  ({ value, className, children, ...props }, ref) => {
    return (
      <AccordionItemContext.Provider value={{ value }}>
        <div ref={ref} className={cn("border-b", className)} {...props}>
          {children}
        </div>
      </AccordionItemContext.Provider>
    )
  }
)
AccordionItem.displayName = "AccordionItem"

interface AccordionTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {}

const AccordionTrigger = React.forwardRef<HTMLButtonElement, AccordionTriggerProps>(
  ({ className, children, ...props }, ref) => {
    const itemContext = React.useContext(AccordionItemContext)
    const { value: openValue, onValueChange } = React.useContext(AccordionContext)
    const itemValue = itemContext?.value
    const isOpen = itemValue !== undefined && openValue === itemValue

    if (!itemValue) {
      console.warn("AccordionTrigger must be used within an AccordionItem")
      return null
    }

    return (
      <div className="flex">
        <button
          ref={ref}
          type="button"
          className={cn(
            "flex flex-1 items-center justify-between py-4 font-medium transition-all hover:underline",
            className
          )}
          onClick={() => onValueChange?.(itemValue)}
          aria-expanded={isOpen}
          {...props}
        >
          {children}
          <ChevronDown
            className={cn(
              "h-4 w-4 shrink-0 transition-transform duration-200",
              isOpen && "rotate-180"
            )}
          />
        </button>
      </div>
    )
  }
)
AccordionTrigger.displayName = "AccordionTrigger"

interface AccordionContentProps extends React.HTMLAttributes<HTMLDivElement> {}

const AccordionContent = React.forwardRef<HTMLDivElement, AccordionContentProps>(
  ({ className, children, ...props }, ref) => {
    const itemContext = React.useContext(AccordionItemContext)
    const { value: openValue } = React.useContext(AccordionContext)
    const itemValue = itemContext?.value
    const isOpen = itemValue !== undefined && openValue === itemValue
    const contentRef = React.useRef<HTMLDivElement>(null)
    const [height, setHeight] = React.useState<string>(isOpen ? "auto" : "0px")

    React.useEffect(() => {
      if (contentRef.current) {
        if (isOpen) {
          setHeight(`${contentRef.current.scrollHeight}px`)
        } else {
          setHeight("0px")
        }
      }
    }, [isOpen])

    // Update height when children change
    React.useEffect(() => {
      if (isOpen && contentRef.current) {
        const timeout = setTimeout(() => {
          if (contentRef.current) {
            setHeight(`${contentRef.current.scrollHeight}px`)
          }
        }, 0)
        return () => clearTimeout(timeout)
      }
    }, [isOpen, children])

    if (!itemValue) {
      console.warn("AccordionContent must be used within an AccordionItem")
      return null
    }

    return (
      <div
        ref={ref}
        className={cn("overflow-hidden text-sm transition-all duration-200", className)}
        style={{ 
          height: height === "auto" ? "auto" : height,
          opacity: isOpen ? 1 : 0,
          transition: "height 200ms ease-out, opacity 200ms ease-out"
        }}
        {...props}
      >
        <div ref={contentRef} className="pb-4 pt-0">
          {children}
        </div>
      </div>
    )
  }
)
AccordionContent.displayName = "AccordionContent"

export { Accordion, AccordionItem, AccordionTrigger, AccordionContent }
