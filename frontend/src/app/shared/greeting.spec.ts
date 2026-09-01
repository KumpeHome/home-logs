import { firstName, timeOfDayGreeting } from './greeting';

describe('timeOfDayGreeting', () => {
  it('uses the first name and a calm morning greeting', () => {
    expect(timeOfDayGreeting(8, 'Sam Kumpe')).toBe('Good morning, Sam');
  });

  it('switches to afternoon and evening without sounding urgent', () => {
    expect(timeOfDayGreeting(14, 'Casey')).toBe('Good afternoon, Casey');
    expect(timeOfDayGreeting(19, 'Ada Admin')).toBe('Good evening, Ada');
  });

  it('falls back to a friendly you when the name is missing', () => {
    expect(firstName(null)).toBe('there');
    expect(timeOfDayGreeting(10, '')).toBe('Good morning, there');
  });
});
