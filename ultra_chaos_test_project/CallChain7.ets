/**
 * 调用链文件 7
 */

import { ChainClass8 } from './CallChain8';

export class ChainClass7 {
    methodA() {
        const next = new ChainClass8();
        return next.methodB();
    }
    
    methodB() {
        return 'Chain7 B';
    }
    
    methodC() {
        this.methodA();
        this.methodB();
        return 'Chain7 C';
    }
}
