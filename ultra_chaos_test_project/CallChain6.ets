/**
 * 调用链文件 6
 */

import { ChainClass7 } from './CallChain7';

export class ChainClass6 {
    methodA() {
        const next = new ChainClass7();
        return next.methodB();
    }
    
    methodB() {
        return 'Chain6 B';
    }
    
    methodC() {
        this.methodA();
        this.methodB();
        return 'Chain6 C';
    }
}
