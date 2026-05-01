---
name: DENTIX Visual Identity
version: "1.0.0"
description: "A calm, healthcare-focused design system utilizing glassmorphism and soft teal/cyan tones."

colors:
  primary: "#0891B2" # Cyan 500
  primary-light: "#E0F2FE"
  primary-dark: "#0E7490"
  
  medical:
    light: "#E0F2FE"
    default: "#0891B2"
    dark: "#155E75"
    
  health:
    light: "#DCFCE7"
    default: "#22C55E"
    dark: "#166534"

  neutral:
    slate-50: "#F8FAFC"
    slate-100: "#F1F5F9"
    slate-200: "#E2E8F0"
    slate-500: "#64748B"
    slate-600: "#475569"
    slate-900: "#0F172A"

  semantic:
    background: "{var(--background)}"
    surface: "{var(--surface)}"
    surface-hover: "{var(--surface-hover)}"
    text-primary: "{var(--text-primary)}"
    text-secondary: "{var(--text-secondary)}"
    border: "{var(--border)}"
    input: "{var(--input)}"

typography:
  fontFamily: "Cairo, sans-serif"
  h1:
    fontSize: "1.875rem" # 30px
    fontWeight: "900"
  body:
    fontSize: "1rem"
    fontWeight: "400"
  label:
    fontSize: "0.875rem"
    fontWeight: "700"

rounded:
  sm: "0.5rem"
  md: "0.75rem"
  lg: "1rem"
  xl: "1.5rem" # Default for cards and major containers

spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"

components:
  card:
    backgroundColor: "{semantic.surface}"
    rounded: "{rounded.xl}"
    border: "1px solid {semantic.border}"
  
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#FFFFFF"
    rounded: "{rounded.lg}"
    padding: "10px 16px"
  
  input:
    backgroundColor: "{semantic.input}"
    rounded: "{rounded.md}"
    border: "1px solid {semantic.border}"

---

## Overview
DENTIX is a premium healthcare management platform designed to provide a "Calm & Comfort" experience for both dentists and patients. The interface relies on clean whitespace, glassmorphism, and a high-trust color palette.

## Colors
The system is built on a foundation of Cyan and Slate.

- **Primary (#0891B2):** Used for primary actions, branding, and active states.
- **Surface:** Uses an 80% opacity glass effect (`rgba(255, 255, 255, 0.8)`) to allow background gradients to peek through, creating depth.
- **Success (#22C55E):** Used for medical "Healthy" states and successful payment confirmations.

## Typography
**Cairo** is the mandatory font family, chosen for its excellent readability in both Arabic and English.
- Use **Black (900)** for page titles to convey authority.
- Use **Bold (700)** for labels and interactive text.
- Use **Medium/Regular** for medical data and descriptions.

## Components
### Cards
Every major container should use the `rounded-2xl` (1.5rem) radius. This softness reduces the "clinical/harsh" feel and makes the software feel more modern and accessible.

### Modals
Modals must use `backdrop-blur-md` on the overlay to maintain focus while keeping the context visible.

### Tabs
Tabs should be consistent across the app. The preferred style is the "Pill" container for secondary navigation and "Underline" for primary page sections.
