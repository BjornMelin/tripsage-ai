import { useState, useCallback } from 'react';
import { z } from 'zod';
import { 
  FlightSearchRequestSchema, 
  AgentStatusSchema,
  AgentMessageSchema,
  type FlightSearchRequest,
  type AgentStatus,
  type AgentMessage
} from '@/lib/schemas/agent';

// Hook for validating agent inputs and outputs
export function useAgentValidation() {
  const [validationErrors, setValidationErrors] = useState<Record<string, string[]>>({});

  // Validate flight search request
  const validateFlightSearch = useCallback((data: unknown): FlightSearchRequest | null => {
    try {
      const validated = FlightSearchRequestSchema.parse(data);
      setValidationErrors({});
      return validated;
    } catch (error) {
      if (error instanceof z.ZodError) {
        const errors: Record<string, string[]> = {};
        error.errors.forEach((err) => {
          const path = err.path.join('.');
          if (!errors[path]) {
            errors[path] = [];
          }
          errors[path].push(err.message);
        });
        setValidationErrors(errors);
      }
      return null;
    }
  }, []);

  // Validate agent status updates
  const validateAgentStatus = useCallback((data: unknown): AgentStatus | null => {
    try {
      return AgentStatusSchema.parse(data);
    } catch (error) {
      console.error('Invalid agent status:', error);
      return null;
    }
  }, []);

  // Validate agent messages
  const validateAgentMessage = useCallback((data: unknown): AgentMessage | null => {
    try {
      return AgentMessageSchema.parse(data);
    } catch (error) {
      console.error('Invalid agent message:', error);
      return null;
    }
  }, []);

  // Clear validation errors
  const clearErrors = useCallback(() => {
    setValidationErrors({});
  }, []);

  return {
    validationErrors,
    validateFlightSearch,
    validateAgentStatus,
    validateAgentMessage,
    clearErrors,
  };
}

// Hook for transforming and validating form data before sending to agents
export function useAgentFormValidation<T extends z.ZodType>(
  schema: T
) {
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [isValid, setIsValid] = useState(false);

  const validate = useCallback((data: unknown): z.infer<T> | null => {
    try {
      const validated = schema.parse(data);
      setErrors({});
      setIsValid(true);
      return validated;
    } catch (error) {
      if (error instanceof z.ZodError) {
        const fieldErrors: Record<string, string[]> = {};
        error.errors.forEach((err) => {
          const field = err.path.join('.');
          if (!fieldErrors[field]) {
            fieldErrors[field] = [];
          }
          fieldErrors[field].push(err.message);
        });
        setErrors(fieldErrors);
        setIsValid(false);
      }
      return null;
    }
  }, [schema]);

  const getFieldError = useCallback((field: string): string | undefined => {
    return errors[field]?.[0];
  }, [errors]);

  const clearFieldError = useCallback((field: string) => {
    setErrors((prev) => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  }, []);

  return {
    validate,
    errors,
    isValid,
    getFieldError,
    clearFieldError,
  };
}

// Example usage in a component
export function FlightSearchAgentForm() {
  const { 
    validate, 
    errors, 
    getFieldError 
  } = useAgentFormValidation(FlightSearchRequestSchema);

  const handleSubmit = (formData: unknown) => {
    const validated = validate(formData);
    if (validated) {
      // Send to agent
      sendToFlightSearchAgent(validated);
    }
  };

  return (
    <form onSubmit={(e) => {
      e.preventDefault();
      const formData = new FormData(e.currentTarget);
      handleSubmit(Object.fromEntries(formData));
    }}>
      <input name="tripId" type="hidden" />
      
      <div>
        <input 
          name="parameters.origin" 
          placeholder="Origin (e.g., JFK)"
          maxLength={3}
        />
        {getFieldError('parameters.origin') && (
          <span className="error">{getFieldError('parameters.origin')}</span>
        )}
      </div>

      <div>
        <input 
          name="parameters.destination" 
          placeholder="Destination (e.g., LAX)"
          maxLength={3}
        />
        {getFieldError('parameters.destination') && (
          <span className="error">{getFieldError('parameters.destination')}</span>
        )}
      </div>

      <button type="submit">Search Flights</button>
    </form>
  );
}

// Async validation hook for API calls
export function useAsyncAgentValidation() {
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<any>(null);

  const validateAsync = useCallback(async <T extends z.ZodType>(
    schema: T,
    data: unknown,
    additionalValidation?: (data: z.infer<T>) => Promise<boolean>
  ): Promise<z.infer<T> | null> => {
    setIsValidating(true);
    
    try {
      // First, validate with Zod
      const validated = schema.parse(data);
      
      // Then, perform additional async validation if provided
      if (additionalValidation) {
        const isValid = await additionalValidation(validated);
        if (!isValid) {
          setValidationResult({ success: false, error: 'Additional validation failed' });
          return null;
        }
      }
      
      setValidationResult({ success: true, data: validated });
      return validated;
    } catch (error) {
      if (error instanceof z.ZodError) {
        setValidationResult({ success: false, error: error.errors });
      } else {
        setValidationResult({ success: false, error: 'Validation failed' });
      }
      return null;
    } finally {
      setIsValidating(false);
    }
  }, []);

  return {
    validateAsync,
    isValidating,
    validationResult,
  };
}