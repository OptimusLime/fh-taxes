import { render, h } from 'preact';
import Deck from '../viz/src/components/purpose/Deck.tsx';
render(h(Deck, null), document.getElementById('deck-root')!);
