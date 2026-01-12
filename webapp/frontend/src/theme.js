// Shared color theme for the application
export const COLORS = {
  // Participant colors for avatars and message bubbles
  participants: [
    '#FFB6C1', '#FFD4B2', '#FFF4B2', '#BAE4FF', '#BAFFC9',
    '#D4BAFF', '#FFB3E6', '#B3E5FC', '#C5E1A5', '#F8BBD0',
    '#FFCCBC', '#D1C4E9', '#B2DFDB', '#FFF9C4', '#F0F4C3'
  ],
  
  // Gradient colors for backgrounds
  gradient: {
    peach: 'rgba(255, 218, 185, 0.15)',
    pink: 'rgba(255, 182, 193, 0.15)',
    lavender: 'rgba(203, 195, 227, 0.15)',
    lightBlue: 'rgba(186, 225, 255, 0.15)',
    green: 'rgba(186, 255, 201, 0.15)'
  },
  
  // Solid gradient colors for headers
  solidGradient: {
    pink: 'rgba(255, 182, 193, 0.8)',
    lavender: 'rgba(203, 195, 227, 0.8)',
    lightBlue: 'rgba(186, 225, 255, 0.8)',
    peach: 'rgba(255, 218, 185, 0.8)'
  },
  
  // Status colors for form checker
  status: {
    valid: '#4CAF50',      // Green for valid/checked
    invalid: '#f44336',    // Red for invalid/not checked
    pending: '#FFA500'     // Orange for pending validation
  }
};

// Gradient definitions
export const GRADIENTS = {
  background: `linear-gradient(
    180deg,
    ${COLORS.gradient.peach} 0%,
    ${COLORS.gradient.pink} 25%,
    ${COLORS.gradient.lavender} 50%,
    ${COLORS.gradient.lightBlue} 75%,
    ${COLORS.gradient.green} 100%
  )`,
  
  header: `linear-gradient(
    90deg,
    ${COLORS.solidGradient.pink} 0%,
    ${COLORS.solidGradient.lavender} 50%,
    ${COLORS.solidGradient.lightBlue} 100%
  )`,
  
  button: `linear-gradient(
    135deg,
    ${COLORS.solidGradient.pink} 0%,
    ${COLORS.solidGradient.peach} 100%
  )`
};
