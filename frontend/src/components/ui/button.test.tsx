import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Button } from './button'

describe('Button', () => {
  it('renders its label as an accessible button', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
  })

  it('applies the destructive variant class', () => {
    render(<Button variant="destructive">Delete</Button>)
    expect(screen.getByRole('button', { name: 'Delete' })).toHaveClass('bg-destructive')
  })
})
