---
alwaysApply: true
---

# Debugging Rule: Start Simple, Stay Systematic

When debugging missing functionality:

1. **Search first, assume nothing**: Use `grep_search` to find ALL instances of similar working code before making changes
2. **Compare working examples**: If feature X works but Y doesn't, immediately compare their exact code paths side-by-side  
3. **Verify basic structure exists**: Check if the code/condition even exists before debugging complex logic
4. **Try simplest explanation first**: Missing code, typos, wrong variable names - not complex architectural problems
5. **Copy working patterns exactly**: Don't reinvent - copy the working implementation and adapt minimally
6. **Avoid elaborate debugging**: Don't add complex logging/debug code until simple fixes are ruled out

Red flags to avoid:
- Adding debug complexity before checking if code exists
- Assuming structure is correct and debugging extraction logic  
- Making multiple changes simultaneously
- Not systematically searching for all relevant code locations

Remember: Most bugs are simple missing pieces, not complex architectural problems. Start with the obvious, stay methodical.